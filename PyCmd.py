import sys, os, msvcrt, tempfile, signal, time, traceback

from common import parse_line, unescape, sep_tokens, sep_chars
from common import split_nocase, abbrev_path
from common import expand_tilde, expand_env_vars
from common import associated_application, full_executable_path, is_gui_application
from completion import complete_file, complete_wildcard, complete_env_var, find_common_prefix, has_wildcards, wildcard_to_regex
from InputState import ActionCode, InputState
from DirHistory import DirHistory
from console import get_text_attributes, set_text_attributes, get_buffer_size, set_console_title
from console import move_cursor, get_cursor, cursor_backward
from console import read_input, write_input
from console import is_ctrl_pressed, is_alt_pressed, is_shift_pressed, is_control_only
from console import scroll_buffer, get_viewport
from console import FOREGROUND_WHITE, FOREGROUND_BRIGHT, FOREGROUND_RED
from console import BACKGROUND_WHITE, BACKGROUND_BLUE, BACKGROUND_GREEN, BACKGROUND_RED

def main():
    # %APPDATA% is not always defined (e.g. when using runas.exe)
    if 'APPDATA' in os.environ.keys():
        APPDATA = '%APPDATA%'
    else:
        APPDATA = '%USERPROFILE%\\Application Data'
    global pycmd_data_dir
    pycmd_data_dir = expand_env_vars(APPDATA + '\\PyCmd')

    # Create app data directory structure if not present
    if not os.path.isdir(pycmd_data_dir):
        os.mkdir(pycmd_data_dir)
    if not os.path.isdir(pycmd_data_dir + '\\tmp'):
        os.mkdir(pycmd_data_dir + '\\tmp')

    # Current state of the input (prompt, entered chars, history)
    global state
    state = InputState()

    # Read/initialize command history
    state.history = read_history(pycmd_data_dir + '\\history')
    state.history_index = len(state.history)

    # Read/initialize directory history
    global dir_hist
    dir_hist = DirHistory()
    dir_hist.locations = read_history(pycmd_data_dir + '\\dir_history')
    dir_hist.index = len(dir_hist.locations) - 1
    dir_hist.visit_cwd()

    # Create temporary file
    global tmpfile
    (handle, tmpfile) = tempfile.mkstemp(dir = pycmd_data_dir + '\\tmp')
    os.close(handle)

    # Catch SIGINT to emulate Ctrl-C key combo
    signal.signal(signal.SIGINT, signal_handler)

    # Default options
    title_prefix = ""
    global quiet_mode
    quiet_mode = False

    # Parse arguments
    arg = 1
    while arg < len(sys.argv):
        switch = sys.argv[arg].upper()
        rest = ['"' + t + '"' if os.path.exists(t) else t
                for t in sys.argv[arg+1:]]
        if switch in ['/K', '-K']:
            # Run the specified command and continue
            if rest != []:
                run_command(rest)
                dir_hist.visit_cwd()
                break
        elif switch in ['/C', '-C']:
            # Run the specified command end exit
            if rest != []:
                run_command(rest)
            internal_exit()
        elif switch in ['/H', '/?', '-H']:
            # Show usage information and exit
            print_usage()
            internal_exit()
        elif switch in ['/T', '-T']:
            if arg == len(sys.argv) - 1:
                sys.stderr.write('PyCmd: no title specified to /T switch\n')
                print_usage()
                internal_exit()
            title_prefix = sys.argv[arg+1] + ' - '
            arg += 1
        elif switch in ['/Q', '-Q']:
            # Quiet mode: suppress messages
            quiet_mode = True
        else:
            # Invalid command line switch
            sys.stderr.write('PyCmd: unrecognized option `' + sys.argv[arg] + '\'\n')
            print_usage()
            internal_exit()
        arg += 1

    if not quiet_mode:
        # Print some splash text
        print
        print 'Welcome to PyCmd 0.7!'
        print

    # Run an empty command to initialize environment
    run_command(['echo', '>', 'NUL'])

    # Main loop
    while True:
        # Prepare buffer for reading one line
        state.reset_line(prompt())
        scrolling = False
        auto_select = False
        force_repaint = True
        dir_hist.shown = False
        print

        while True:
            # Update console title and environment
            curdir = os.getcwd()
            curdir = curdir[0].upper() + curdir[1:]
            set_console_title(title_prefix + curdir + ' - PyCmd')
            os.environ['CD'] = curdir

            # Save default (original) text attributes
            orig_attr = get_text_attributes()

            if state.changed() or force_repaint:
                prev_total_len = len(state.prev_prompt + state.prev_before_cursor + state.prev_after_cursor)
                cursor_backward(len(state.prev_prompt + state.prev_before_cursor))
                sys.stdout.write('\r')

                # Update the offset of the directory history in case of overflow
                # Note that if the history display is marked as 'dirty'
                # (dir_hist.shown == False) the result of this action can be
                # ignored
                dir_hist.check_overflow(state.prompt)

                # Write current line
                set_text_attributes(orig_attr ^ FOREGROUND_BRIGHT)       # Revert brightness bit for prompt
                sys.stdout.write('\r' + state.prompt)
                if state.history_filter == '':
                    line = state.before_cursor + state.after_cursor
                    cursor = len(state.before_cursor)
                    sel_start, sel_end = state.get_selection_range()
                    set_text_attributes(orig_attr)
                    sys.stdout.write(line[:sel_start])
                    set_text_attributes(orig_attr ^ FOREGROUND_WHITE ^ BACKGROUND_WHITE)
                    sys.stdout.write(line[sel_start: sel_end])
                    set_text_attributes(orig_attr)
                    sys.stdout.write(line[sel_end:])
                else:
                    # print '\n\n', (before_cursor + after_cursor).split(history_filter), '\n\n'
                    (chunks, seps) = split_nocase(state.before_cursor + state.after_cursor, state.history_filter)
                    # print '\n\n', chunks, seps, '\n\n'
                    for i in range(len(chunks)):
                        set_text_attributes(orig_attr)
                        sys.stdout.write(chunks[i])
                        if i < len(chunks) - 1:
                            set_text_attributes(orig_attr ^ BACKGROUND_BLUE ^ BACKGROUND_RED ^ FOREGROUND_BRIGHT)
                            sys.stdout.write(seps[i])
                    set_text_attributes(orig_attr)

                # Erase remaining chars from old line
                to_erase = prev_total_len - len(state.prompt + state.before_cursor + state.after_cursor)
                if to_erase > 0:
                    for i in range(to_erase):
                        sys.stdout.write(' ')
                    cursor_backward(to_erase)
                cursor_backward(len(state.after_cursor))

            # Prepare new input state
            state.step_line()

            # Read and process a keyboard event
            rec = read_input()
            select = auto_select or is_shift_pressed(rec)

            # Will be overriden if Shift-PgUp/Dn is pressed
            force_repaint = not is_control_only(rec)    

            #print '\n\n', rec.keyDown, rec.char, rec.virtualKeyCode, rec.controlKeyState, '\n\n'
            if is_ctrl_pressed(rec) and not is_alt_pressed(rec):  # Ctrl-Something
                if rec.char == chr(4):                  # Ctrl-D
                    if state.before_cursor + state.after_cursor == '':
                        internal_exit('\r\nBye!')
                    else:
                        state.handle(ActionCode.ACTION_DELETE)
                elif rec.char == chr(31):                   # Ctrl-_
                    state.handle(ActionCode.ACTION_UNDO_EMACS)
                    auto_select = False
                elif rec.virtualKeyCode == 75:          # Ctrl-K
                    state.handle(ActionCode.ACTION_KILL_EOL)
                elif rec.virtualKeyCode == 32:          # Ctrl-Space
                    auto_select = True
                    state.reset_selection()
                elif rec.virtualKeyCode == 71:          # Ctrl-G
                    if scrolling:
                        scrolling = False
                    else:
                        state.handle(ActionCode.ACTION_ESCAPE)
                        save_history(state.history,
                                     pycmd_data_dir + '\\history',
                                     1000)
                elif rec.virtualKeyCode == 65:          # Ctrl-A
                    state.handle(ActionCode.ACTION_HOME, select)
                elif rec.virtualKeyCode == 69:          # Ctrl-E
                    state.handle(ActionCode.ACTION_END, select)
                elif rec.virtualKeyCode == 66:          # Ctrl-B
                    state.handle(ActionCode.ACTION_LEFT, select)
                elif rec.virtualKeyCode == 70:          # Ctrl-F
                    state.handle(ActionCode.ACTION_RIGHT, select)
                elif rec.virtualKeyCode == 80:          # Ctrl-P
                    state.handle(ActionCode.ACTION_PREV)
                elif rec.virtualKeyCode == 78:          # Ctrl-N
                    state.handle(ActionCode.ACTION_NEXT)
                elif rec.virtualKeyCode == 37:          # Ctrl-Left
                    state.handle(ActionCode.ACTION_LEFT_WORD, select)
                elif rec.virtualKeyCode == 39:          # Ctrl-Right
                    state.handle(ActionCode.ACTION_RIGHT_WORD, select)
                elif rec.virtualKeyCode == 46:          # Ctrl-Delete
                    state.handle(ActionCode.ACTION_DELETE_WORD)
                elif rec.virtualKeyCode == 67:          # Ctrl-C
                    # The Ctrl-C signal is caught by our custom handler, and a
                    # synthetic keyboard event is created so that we can catch
                    # it here
                    if state.get_selection() != '':
                        state.handle(ActionCode.ACTION_COPY)
                    else:
                        state.handle(ActionCode.ACTION_ESCAPE)
                    auto_select = False
                elif rec.virtualKeyCode == 88:          # Ctrl-X
                    state.handle(ActionCode.ACTION_CUT)
                    auto_select = False
                elif rec.virtualKeyCode == 87:          # Ctrl-W
                    state.handle(ActionCode.ACTION_CUT)
                    auto_select = False
                elif rec.virtualKeyCode == 86:          # Ctrl-V
                    state.handle(ActionCode.ACTION_PASTE)
                    auto_select = False
                elif rec.virtualKeyCode == 89:          # Ctrl-Y
                    state.handle(ActionCode.ACTION_PASTE)
                    auto_select = False
                elif rec.virtualKeyCode == 8:           # Ctrl-Backspace
                    state.handle(ActionCode.ACTION_BACKSPACE_WORD)
                elif rec.virtualKeyCode == 90:  
                    if not is_shift_pressed(rec):       # Ctrl-Z
                        state.handle(ActionCode.ACTION_UNDO)
                    else:                               # Ctrl-Shift-Z
                        state.handle(ActionCode.ACTION_REDO)
                    auto_select = False
            elif is_alt_pressed(rec) and not is_ctrl_pressed(rec):      # Alt-Something
                if rec.virtualKeyCode in [37, 39] + range(49, 59):      # Dir history 
                    if state.before_cursor + state.after_cursor == '':
                        state.reset_prev_line()
                        if rec.virtualKeyCode == 37:            # Alt-Left
                            changed = dir_hist.go_left()
                        elif rec.virtualKeyCode == 39:          # Alt-Right     
                            changed = dir_hist.go_right()
                        else:                                   # Alt-1..Alt-9        
                            changed = dir_hist.jump(rec.virtualKeyCode - 48)
                        if changed:
                            state.prev_prompt = state.prompt
                            state.prompt = prompt()
                        save_history(dir_hist.locations,
                                     pycmd_data_dir + '\\dir_history',
                                     dir_hist.max_len)
                        if dir_hist.shown:
                            dir_hist.display()
                            sys.stdout.write(state.prev_prompt)
                    else:
                        if rec.virtualKeyCode == 37:            # Alt-Left
                            state.handle(ActionCode.ACTION_LEFT_WORD, select)
                        elif rec.virtualKeyCode == 39:          # Alt-Right
                            state.handle(ActionCode.ACTION_RIGHT_WORD, select)
                elif rec.virtualKeyCode == 66:          # Alt-B
                    state.handle(ActionCode.ACTION_LEFT_WORD, select)
                elif rec.virtualKeyCode == 70:          # Alt-F
                    state.handle(ActionCode.ACTION_RIGHT_WORD, select)
                elif rec.virtualKeyCode == 80:          # Alt-P
                    state.handle(ActionCode.ACTION_PREV)
                elif rec.virtualKeyCode == 78:          # Alt-N
                    state.handle(ActionCode.ACTION_NEXT)
                elif rec.virtualKeyCode == 68:          # Alt-D
                    if state.before_cursor + state.after_cursor == '':
                        dir_hist.display()
                        dir_hist.check_overflow(state.prev_prompt)
                        sys.stdout.write(state.prev_prompt)
                    else:
                        state.handle(ActionCode.ACTION_DELETE_WORD) 
                elif rec.virtualKeyCode == 87:          # Alt-W
                    state.handle(ActionCode.ACTION_COPY)
                    state.reset_selection()
                    auto_select = False
                elif rec.virtualKeyCode == 46:          # Alt-Delete
                    state.handle(ActionCode.ACTION_DELETE_WORD)
                elif rec.virtualKeyCode == 8:           # Alt-Backspace
                    state.handle(ActionCode.ACTION_BACKSPACE_WORD)
                elif rec.virtualKeyCode == 191:
                    state.handle(ActionCode.ACTION_EXPAND)
            elif is_shift_pressed(rec) and rec.virtualKeyCode == 33:    # Shift-PgUp
                (_, t, _, b) = get_viewport()
                scroll_buffer(t - b + 2)
                scrolling = True
                force_repaint = False
            elif is_shift_pressed(rec) and rec.virtualKeyCode == 34:    # Shift-PgDn
                (_, t, _, b) = get_viewport()
                scroll_buffer(b - t - 2)
                scrolling = True
                force_repaint = False
            else:                                       # Clean key (no modifiers)
                if rec.char == chr(0):                  # Special key (arrows and such)
                    if rec.virtualKeyCode == 37:        # Left arrow
                        state.handle(ActionCode.ACTION_LEFT, select)
                    elif rec.virtualKeyCode == 39:      # Right arrow
                        state.handle(ActionCode.ACTION_RIGHT, select)
                    elif rec.virtualKeyCode == 36:      # Home
                        state.handle(ActionCode.ACTION_HOME, select)
                    elif rec.virtualKeyCode == 35:      # End
                        state.handle(ActionCode.ACTION_END, select)
                    elif rec.virtualKeyCode == 38:      # Up arrow
                        state.handle(ActionCode.ACTION_PREV)
                    elif rec.virtualKeyCode == 40:      # Down arrow
                        state.handle(ActionCode.ACTION_NEXT)
                    elif rec.virtualKeyCode == 46:      # Delete
                        state.handle(ActionCode.ACTION_DELETE)
                elif rec.char == chr(13):               # Enter
                    state.reset_history()
                    break
                elif rec.char == chr(27):               # Esc
                    if scrolling:
                        scrolling = False
                    else:
                        state.handle(ActionCode.ACTION_ESCAPE)
                        save_history(state.history, 
                                     pycmd_data_dir + '\\history',
                                     1000)
                elif rec.char == '\t':                  # Tab
                    sys.stdout.write(state.after_cursor)        # Move cursor to the end

                    tokens = parse_line(state.before_cursor)
                    if tokens == [] or state.before_cursor[-1] in sep_chars:
                        tokens.append('')   # This saves some checks later on
                    if tokens[-1].strip('"').count('%') % 2 == 1 or tokens[-1].strip('"').endswith('%'):
                        (completed, suggestions) = complete_env_var(state.before_cursor)
                    elif has_wildcards(tokens[-1]):
                        (completed, suggestions)  = complete_wildcard(state.before_cursor)
                    else:
                        (completed, suggestions)  = complete_file(state.before_cursor)

                    # Show multiple completions if available
                    if len(suggestions) > 1:
                        dir_hist.shown = False  # The displayed dirhist is no longer valid
                        column_width = max([len(s) for s in suggestions]) + 10
                        if column_width > get_buffer_size()[0] - 1:
                            column_width = get_buffer_size()[0] - 1
                        if len(suggestions) > (get_viewport()[3] - get_viewport()[1]) / 4:
                            # We print multiple columns to save space
                            num_columns = (get_buffer_size()[0] - 1) / column_width
                        else:
                            # We print a single column for clarity
                            num_columns = 1
                        num_lines = len(suggestions) / num_columns
                        if len(suggestions) % num_columns != 0:
                            num_lines += 1

                        num_screens = 1.0 * num_lines / (get_viewport()[3] - get_viewport()[1])
                        if num_screens >= 0.9:
                            # We ask for confirmation before displaying many completions
                            (c_x, c_y) = get_cursor()
                            offset_from_bottom = get_buffer_size()[1] - c_y
                            message = ' Scroll ' + str(int(round(num_screens))) + ' screens? [Tab] '
                            sys.stdout.write('\n' + message)
                            rec = read_input()
                            move_cursor(c_x, get_buffer_size()[1] - offset_from_bottom)
                            sys.stdout.write('\n' + ' ' * len(message))
                            move_cursor(c_x, get_buffer_size()[1] - offset_from_bottom)
                            if rec.char != '\t':
                                continue
                            
                        sys.stdout.write('\n')
                        for line in range(0, num_lines):
                            # Print one line
                            sys.stdout.write('\r')
                            for column in range(0, num_columns):
                                if line + column * num_lines < len(suggestions):
                                    s = suggestions[line + column * num_lines]
                                    if has_wildcards(tokens[-1]):
                                        # Print wildcard matches in a different color
                                        tokens = parse_line(completed.rstrip('\\'))
                                        token = tokens[-1].replace('"', '')
                                        (_, _, prefix) = token.rpartition('\\')
                                        match = wildcard_to_regex(prefix + '*').match(s)
                                        current_index = 0
                                        for i in range(1, match.lastindex + 1):
                                            set_text_attributes(orig_attr ^ FOREGROUND_RED)
                                            sys.stdout.write(s[current_index : match.start(i)])
                                            set_text_attributes(orig_attr)
                                            sys.stdout.write(s[match.start(i) : match.end(i)])
                                            current_index = match.end(i)
                                        sys.stdout.write(' ' * (column_width - len(s)))
                                    else:
                                        # Print the common part in a different color
                                        common_prefix_len = len(find_common_prefix(state.before_cursor, suggestions))
                                        set_text_attributes(orig_attr ^ FOREGROUND_RED)
                                        sys.stdout.write(s[:common_prefix_len])
                                        set_text_attributes(orig_attr)
                                        sys.stdout.write(s[common_prefix_len : ])
                                        sys.stdout.write(' ' * (column_width - len(s)))
                            sys.stdout.write('\n')
                            line += 1
                        state.reset_prev_line()
                    state.handle(ActionCode.ACTION_COMPLETE, completed)
                elif rec.char == chr(8):                # Backspace
                    state.handle(ActionCode.ACTION_BACKSPACE)
                else:                                   # Regular character
                    state.handle(ActionCode.ACTION_INSERT, rec.char)


        # Done reading line, now execute
        sys.stdout.write(state.after_cursor)        # Move cursor to the end
        line = (state.before_cursor + state.after_cursor).strip()
        tokens = parse_line(line)
        if tokens == [] or tokens[0] == '':
            continue
        else:
            print
            run_command(tokens)

        # Add to history
        state.add_to_history(line)
        save_history(state.history,
                     pycmd_data_dir + '\\history',
                     1000)


        # Add to dir history
        dir_hist.visit_cwd()
        save_history(dir_hist.locations,
                     pycmd_data_dir + '\\dir_history',
                     dir_hist.max_len)


def internal_cd(args):
    """The internal CD command"""
    try:
        if len(args) == 0:
            os.chdir(expand_env_vars('~'))
        else:
            target = args[0]
            if target != '\\' and target[1:] != ':\\':
                target = target.rstrip('\\')
            target = expand_env_vars(target.strip('"').strip(' '))
            os.chdir(target)
    except OSError, error:
        sys.stdout.write('\n' + str(error))
    os.environ['CD'] = os.getcwd()


def internal_exit(message = ''):
    """The EXIT command, with an optional goodbye message"""
    global quiet_mode
    if ((not quiet_mode) and message != ''):
        print message
    os.remove(tmpfile)
    sys.exit()


def run_command(tokens):
    """Execute a command line (treat internal and external appropriately"""
    if tokens[0] == 'exit':
        internal_exit('Bye!')
    elif tokens[0].lower() == 'cd' and [t for t in tokens if t in sep_tokens] == []:
        # This is a single CD command -- use our custom, more handy CD
        internal_cd([unescape(t) for t in tokens[1:]])
    else:
        if set(sep_tokens).intersection(tokens) == set([]):
            # This is a simple (non-compound) command
            # Crude hack so that we return to the prompt when starting GUI
            # applications: if we think that the first token on the given command
            # line is an executable, check its PE header to decide whether it's
            # GUI application. If it is, spawn the process and then get on with
            # life.
            cmd = expand_env_vars(tokens[0].strip('"'))
            dir, name = os.path.split(cmd)
            ext = os.path.splitext(name)[1]

            if ext in ['', '.exe', '.com', '.bat', '.cmd']:
                # Executable given
                app = cmd
            else:
                # Not an executable -- search for the associated application
                if os.path.isfile(cmd):
                    app = associated_application(ext)
                else:
                    # No application will be spawned if the file doesn't exist
                    app = None

            if app:
                executable = full_executable_path(app)
                if executable and os.path.splitext(executable)[1].lower() == '.exe':
                    # This is an exe file, try to figure out whether it's a GUI
                    # or console application
                    if is_gui_application(executable):
                        import subprocess
                        subprocess.Popen('"' + ' '.join([expand_tilde(t) for t in tokens]) + '"', shell=True)
                        return

        # Regular (external) command
        run_in_cmd(tokens)


def run_in_cmd(tokens):
    pseudo_vars = ['CD', 'DATE', 'ERRORLEVEL', 'RANDOM', 'TIME']

    line_sanitized = ''
    for token in tokens:
        token_sane = expand_tilde(token)
        if token_sane != '\\' and token_sane[1:] != ':\\':
            token_sane = token_sane.rstrip('\\')
        if token_sane.count('"') % 2 == 1:
            token_sane += '"'
        line_sanitized += token_sane + ' '
    line_sanitized = line_sanitized[:-1]
    if line_sanitized.endswith('&') and not line_sanitized.endswith('^&'):
        # We remove a redundant & to avoid getting an 'Unexpected &' error when
        # we append a new one below; the ending & it would be ignored by cmd.exe
        # anyway...
        line_sanitized = line_sanitized[:-1]
    elif line_sanitized.endswith('|') and not line_sanitized.endswith('^|') \
            or line_sanitized.endswith('&&') and not line_sanitized.endswith('^&&'):
        # The syntax of the command is incorrect, cmd would refuse to execute it
        # altogether; in order to we replicate the error message, we run a simple
        # invalid command and return
        print
        os.system('echo |')
        return

    # Cleanup environment
    for var in pseudo_vars:
        if var in os.environ.keys():
            del os.environ[var]

    # Run command
    if line_sanitized != '':
        command = '"'
        command += line_sanitized
        command += ' &set > "' + tmpfile + '"'
        for var in pseudo_vars:
            command += ' & echo ' + var + '="%' + var + '%" >> "' + tmpfile + '"'
        command += '& <nul (set /p xxx=CD=) >>"' + tmpfile + '" & cd >>"' + tmpfile + '"'
        command +=  '"'
        os.system(command)

    # Update environment and state
    new_environ = {}
    env_file = open(tmpfile, 'r')
    for l in env_file.readlines():
        [variable, value] = l.split('=', 1)
        value = value.rstrip('\n ')
        if variable in pseudo_vars:
            value = value.strip('"')
        new_environ[variable] = value
    env_file.close()
    if new_environ != {}:
        for variable in os.environ.keys():
            if not variable in new_environ.keys() \
                   and sorted(new_environ.keys()) != sorted(pseudo_vars):
                del os.environ[variable]
        for variable in new_environ:
            os.environ[variable] = new_environ[variable]
    os.chdir(os.environ['CD'])


def prompt():
    """Return a custom prompt"""
    curdir = os.getcwd()
    curdir = curdir[0].upper() + curdir[1:]
    return abbrev_path(curdir) + '> '


def signal_handler(signum, frame):
    """
    Signal handler that catches SIGINT and emulates the Ctrl-C
    keyboard combo
    """
    if signum == signal.SIGINT:
        # Emulate a Ctrl-C press
        write_input(67, 0x0008)


def save_history(lines, filename, length):
    """
    Save a list of unique lines into a history file and truncate the
    result to the given maximum number of lines
    """
    if os.path.isfile(filename):
        # Read previously saved history and merge with current
        history_file = open(filename, 'r')
        history_to_save = [line.rstrip('\n') for line in history_file.readlines()]
        history_file.close()
        for line in lines:
            if line in history_to_save:
                history_to_save.remove(line)
            history_to_save.append(line)
    else:
        # No previous history, save current
        history_to_save = lines

    if len(history_to_save) > length:
        history_to_save = history_to_save[-length :]    # Limit history file

    # Write merged history to history file
    history_file = open(filename, 'w')
    history_file.writelines([line + '\n' for line in history_to_save])
    history_file.close()


def read_history(filename):
    """
    Read and return a list of lines from a history file
    """
    if os.path.isfile(filename):
        history_file = open(filename, 'r')
        history = [line.rstrip('\n') for line in history_file.readlines()]
        history_file.close()
    else:
        print 'Warning: Can\'t open ' + os.path.basename(filename) + '!'
        history = []
    return history


def print_usage():
    """Print usage information"""
    print 'Usage:'
    print '\t PyCmd [-t title] ( [-c command] | [-k command] | [-h] )'
    print
    print '\t\t-c command \tRun command, then exit'
    print '\t\t-k command \tRun command, then continue to the prompt'
    print '\t\t-t title \tShow title in window caption'
    print '\t\t-q\t\tQuiet (suppress messages)'
    print '\t\t-h \t\tShow this help'
    print
    print 'Note that you can use \'/\' instead of \'-\', uppercase instead of '
    print 'lowercase and \'/?\' instead of \'-h\''


# Entry point
if __name__ == '__main__':
    try:
        main()
    except Exception, e:        
        global pycmd_data_dir
        report_file_name = (pycmd_data_dir
                            + '\\crash-' 
                            + time.strftime('%Y%m%d_%H%M%S') 
                            + '.log')
        print '\n'
        print '************************'
        print 'Internal error in PyCmd!' 
        report_file = open(report_file_name, 'w')
        traceback.print_exc(file=report_file)
        report_file.close()
        traceback.print_exc()
        print 
        print 'Crash report written to:\n  ' + report_file_name
        print 'Exiting... sorry :('
        print '************************'
