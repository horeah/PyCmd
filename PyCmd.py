import sys, os, msvcrt, tempfile, signal, time

from common import parse_line, unescape, split_nocase, abbrev_path, sep_tokens
from common import expand_tilde, expand_env_vars
from completion import complete_file, complete_env_var, find_common_prefix
from InputState import ActionCode, InputState
from DirHistory import DirHistory
from console import get_text_attributes, set_text_attributes, get_buffer_size, set_console_title
from console import move_cursor, get_cursor, cursor_backward, set_cursor_visible
from console import read_input, is_ctrl_pressed, is_alt_pressed, is_shift_pressed, is_control_only
from console import scroll_buffer, get_viewport
from console import FOREGROUND_WHITE, FOREGROUND_BRIGHT, FOREGROUND_RED
from console import BACKGROUND_WHITE, BACKGROUND_BLUE, BACKGROUND_GREEN, BACKGROUND_RED

def main():

    # Splash
    print
    print 'Welcome to PyCmd 0.5!'

    # Create directory structure in %APPDATA% if not present
    if not os.path.isdir(expand_env_vars('%APPDATA%\\PyCmd')):
        os.mkdir(expand_env_vars('%APPDATA%\\PyCmd'))
    if not os.path.isdir(expand_env_vars('%APPDATA%\\PyCmd\\tmp')):
        os.mkdir(expand_env_vars('%APPDATA%\\PyCmd\\tmp'))


    # Current state of the input (prompt, entered chars, history)
    global state
    state = InputState()

    # Read/initialize command history
    state.history = read_history(expand_env_vars('%APPDATA%\\PyCmd\\history'))
    state.history_index = len(state.history)

    # Read/initialize directory history
    global dir_hist
    dir_hist = DirHistory()
    dir_hist.locations = read_history(expand_env_vars('%APPDATA%\\PyCmd\\dir_history'))
    dir_hist.index = len(dir_hist.locations) - 1
    dir_hist.visit_cwd()

    # Create temporary file
    global tmpfile
    (handle, tmpfile) = tempfile.mkstemp(dir = expand_env_vars('%APPDATA%\\PyCmd\\tmp'))
    os.close(handle)

    # Catch SIGINT to emulate Ctrl-C key combo
    signal.signal(signal.SIGINT, signal_handler)

    # Run an empty command to initialize environment
    run_in_cmd(['echo', '>', 'NUL'])

    # Main loop
    while True:
        # Prepare buffer for reading one line
        state.reset_line(prompt())
        scrolling = False
        auto_select = False
        force_repaint = True
        dir_hist_shown = False
        print

        while True:
            # Update console title and environment
            curdir = os.getcwd()
            curdir = curdir[0].upper() + curdir[1:]
            set_console_title(curdir + ' - PyCmd')
            os.environ['CD'] = curdir

            # Save default (original) text attributes
            orig_attr = get_text_attributes()

            if state.changed() or force_repaint:
                prev_total_len = len(state.prev_prompt + state.prev_before_cursor + state.prev_after_cursor)
                cursor_backward(len(state.prev_prompt + state.prev_before_cursor))
                
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
                        internal_exit()
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
                                     expand_env_vars('%APPDATA%\\PyCmd\\history'),
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
                    state.handle(ActionCode.ACTION_COPY)
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
            elif is_alt_pressed(rec) and not is_ctrl_pressed(rec): # Alt-Something
                if rec.virtualKeyCode == 37:            # Alt-Left
                    if state.before_cursor + state.after_cursor == '':
                        state.reset_prev_line()
                        if dir_hist.go_left():
                            state.prev_prompt = state.prompt
                            state.prompt = prompt()
                        else:
                            dir_hist_shown = False
                        save_history(dir_hist.locations,
                                     expand_env_vars('%APPDATA%\\PyCmd\\dir_history'),
                                     16)
                        if dir_hist_shown and get_buffer_size()[0] == sx_old:
                            move_cursor(cx_old, cy_old)
                            dir_hist.display()
                            sys.stdout.write(state.prev_prompt)
                    else:
                        state.handle(ActionCode.ACTION_LEFT_WORD, select)
                elif rec.virtualKeyCode == 39:          # Alt-right
                    if state.before_cursor + state.after_cursor == '':
                        state.reset_prev_line()
                        if dir_hist.go_right():
                            state.prev_prompt = state.prompt
                            state.prompt = prompt()
                        else:
                            dir_hist_shown = False
                        save_history(dir_hist.locations,
                                     expand_env_vars('%APPDATA%\\PyCmd\\dir_history'),
                                     16)
                        if dir_hist_shown and get_buffer_size()[0] == sx_old:
                            move_cursor(cx_old, cy_old)
                            dir_hist.display()
                            sys.stdout.write(state.prev_prompt)
                    else:
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
                        sx_current = get_buffer_size()[0]
                        if not dir_hist_shown or sx_old != sx_current:
                            # We need to redisplay the directory history
                            (cx_old, cy_old) = get_cursor()
                            sx_old = sx_current
                            dir_hist.display()
                            dir_hist_shown = True
                            state.reset_prev_line()
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
                                     expand_env_vars('%APPDATA%\\PyCmd\\history'),
                                     1000)
                elif rec.char == '\t':                  # Tab
                    sys.stdout.write(state.after_cursor)        # Move cursor to the end
                    tokens = parse_line(state.before_cursor)
                    if tokens == []:
                        tokens = ['']   # This saves some checks later on
                    if tokens[-1].strip('"').count('%') % 2 == 1 or tokens[-1].strip('"').endswith('%'):
                        (completed, suggestions) = complete_env_var(state.before_cursor)
                    else:
                        (completed, suggestions)  = complete_file(state.before_cursor)
                    if suggestions != []:
                        dir_hist_shown = False  # The displayed dirhist is no longer valid
                        sys.stdout.write('\n')
                        common_prefix_len = len(find_common_prefix(state.before_cursor, suggestions))
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
                        for line in range(0, num_lines):
                            # Print one more line
                            sys.stdout.write('\r')
                            for column in range(0, num_columns):
                                if line + column * num_lines < len(suggestions):
                                    s = suggestions[line + column * num_lines]
                                    # Print the common part in a different color
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
        elif tokens[0] == 'exit':
            internal_exit()
        elif tokens[0].lower() == 'cd' and [t for t in tokens if t in sep_tokens] == []:
            # This is a single CD command -- use our custom, more handy CD
            internal_cd([unescape(t) for t in tokens[1:]])
        else:
            # Regular (external) command
            run_in_cmd(tokens)

        # Add to history
        state.add_to_history(line)
        save_history(state.history,
                     expand_env_vars('%APPDATA%\\PyCmd\\history'),
                     1000)


        # Add to dir history
        dir_hist.visit_cwd()
        save_history(dir_hist.locations,
                     expand_env_vars('%APPDATA%\\PyCmd\\dir_history'),
                     16)


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
    sys.stdout.write('\n')
    os.environ['CD'] = os.getcwd()


def internal_exit():
    """The EXIT command"""
    print
    print 'Bye!'
    os.remove(tmpfile)
    sys.exit()


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
    print

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
        state.handle(ActionCode.ACTION_COPY)


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

# Entry point
if __name__ == '__main__':
    main()
