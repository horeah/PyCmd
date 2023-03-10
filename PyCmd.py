import sys, os, tempfile, signal, time, traceback, codecs, platform
from common import tokenize, unescape, sep_tokens, sep_chars, exec_extensions, pseudo_vars
from common import expand_tilde, expand_env_vars
from common import associated_application, full_executable_path, is_gui_application
from completion import complete_file, complete_wildcard, complete_env_var, find_common_prefix, has_wildcards, wildcard_to_regex, ends_in_env_var
from InputState import ActionCode, InputState
from DirHistory import DirHistory
import console
import re
from sys import stdout, stderr
from console import move_cursor, get_cursor, cursor_backward, erase_to, set_cursor_attributes
from console import read_input, write_input
from console import is_ctrl_pressed, is_alt_pressed, is_shift_pressed, is_control_only
from console import scroll_buffer, get_viewport, scroll_to_quarter, get_buffer_size
from console import remove_escape_sequences
from Window import Window
from pycmd_public import color, appearance, behavior
from common import apply_settings, sanitize_settings
from console.console_common import debug

if sys.platform == 'linux':
    import pty_control


pycmd_data_dir = None
pycmd_install_dir = None
state = None
dir_hist = None
pushd_stack = []
tmpfile = None
save_history_limit = 2000

def init():
    global pycmd_data_dir
    if sys.platform == 'win32':
        # %APPDATA% is not always defined (e.g. when using runas.exe)
        if 'APPDATA' in os.environ.keys():
            APPDATA = '%APPDATA%'
        else:
            APPDATA = '%USERPROFILE%\\Application Data'
        pycmd_data_dir = expand_env_vars(APPDATA + '\\PyCmd')
    else:
        pycmd_data_dir = os.path.expanduser('~/.PyCmd')

    # Create app data directory structure if not present
    if not os.path.isdir(pycmd_data_dir):
        os.mkdir(pycmd_data_dir)
    if not os.path.isdir(pycmd_data_dir + '/tmp'):
        os.mkdir(pycmd_data_dir + '/tmp')

    # Determine the "installation" directory
    global pycmd_install_dir
    pycmd_install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    # Current state of the input (prompt, entered chars, history)
    global state
    state = InputState()

    # Read/initialize command history
    state.history.list = read_history(pycmd_data_dir + '/history')

    # Read/initialize directory history
    global dir_hist
    dir_hist = DirHistory()
    dir_hist.locations = read_history(pycmd_data_dir + '/dir_history')
    dir_hist.index = len(dir_hist.locations) - 1
    dir_hist.visit_cwd()

    # Create temporary file
    global tmpfile
    (handle, tmpfile) = tempfile.mkstemp(dir = pycmd_data_dir + '/tmp')
    os.close(handle)

    # Catch SIGINT to emulate Ctrl-C key combo
    signal.signal(signal.SIGINT, signal_handler)

def deinit():
    if os.path.isfile(tmpfile):
        os.remove(tmpfile)

def main():
    title_prefix = ""

    # Apply global and user configurations
    apply_settings(pycmd_install_dir + '/init.py')
    apply_settings(pycmd_data_dir + '/init.py')
    sanitize_settings()

    os.environ['ERRORLEVEL'] = '0'

    if sys.platform == 'win32':
        # Run an empty command to initialize environment
        run_command(['echo', '>', 'NUL'])
    else:
        # Start a bash instance and control its pty
        pty_control.start(env_dump_file=tmpfile)
        
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
                stderr.write('PyCmd: no title specified to \'-t\'\n')
                print_usage()
                internal_exit()
            title_prefix = sys.argv[arg + 1] + ' - '
            arg += 1
        elif switch in ['/I', '-I']:
            if arg == len(sys.argv) - 1:
                stderr.write('PyCmd: no script specified to \'-i\'\n')
                print_usage()
                internal_exit()
            apply_settings(sys.argv[arg + 1])
            sanitize_settings()
            arg += 1
        elif switch in ['/Q', '-Q']:
            # Quiet mode: suppress messages
            behavior.quiet_mode = True
        elif switch in ['/V:ON', '-V:ON']:
            # Enable delayed expansion (already on by default)
            behavior.delayed_expansion = True
        elif switch in ['/V:OFF', '-V:OFF']:
            # Disable delayed expansion
            behavior.delayed_expansion = False
        else:
            # Invalid command line switch
            stderr.write('PyCmd: unrecognized option `' + sys.argv[arg] + '\'\n')
            print_usage()
            internal_exit()
        arg += 1

    # Re-scan console colors in case the -k command has changed them
    color.Fore.DEFAULT = console.get_current_foreground()
    color.Back.DEFAULT = console.get_current_background()

    if not behavior.quiet_mode:
        # Print some splash text
        arch_names = { '32bit': 'x86', '64bit': 'x64' }
        bits = platform.architecture()[0]
        try:
            from buildinfo import build_date
        except ImportError as ie:
            build_date = '<no build date>'
        print()
        print('Welcome to PyCmd %s-%s!' % (build_date, arch_names[bits]))
        print()

    # Main loop
    while True:
        # Prepare buffer for reading one line
        state.reset_line(appearance.prompt())
        scrolling = False
        auto_select = False
        force_repaint = True
        print()

        while True:
            # Update console title and environment
            curdir = os.getcwd()
            curdir = curdir[0].upper() + curdir[1:]
            console.set_console_title(title_prefix + curdir + ' - PyCmd')
            os.environ['CD'] = curdir

            # Update cursor appearance based on state
            if state.search_substr is not None:
                cursor_height = 30
            elif state.overwrite:
                cursor_height = 50
            else:
                cursor_height = 10

            if state.changed() or force_repaint:
                prev_total_len = len(remove_escape_sequences(state.prev_prompt) + state.prev_before_cursor + state.prev_after_cursor + state.prev_suggestion)
                set_cursor_attributes(cursor_height, False)
                cursor_backward(len(remove_escape_sequences(state.prev_prompt) + state.prev_before_cursor))
                stdout.write('\r')

                # Write current line
                stdout.write(u'\r' + color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.prompt +
                          state.prompt +
                          color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.text)
                line = state.before_cursor + state.after_cursor
                if state.history.filter == '':
                    sel_start, sel_end = state.get_selection_range()
                    stdout.write(line[:sel_start] +
                                 appearance.colors.selection +
                                 line[sel_start: sel_end] +
                                 color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.text +
                                 line[sel_end:])
                    stdout.write(appearance.colors.suggestion + state.suggestion + color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.text)
                else:
                    pos = 0
                    colored_line = ''
                    for (start, end) in state.history.current()[1]:
                        colored_line += color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.text + line[pos : start]
                        colored_line += appearance.colors.search_filter + line[start : end]
                        pos = end
                    colored_line += color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.text + line[pos:]
                    stdout.write(colored_line)

                # Erase remaining chars from old line
                to_erase = prev_total_len - len(remove_escape_sequences(state.prompt) + state.before_cursor + state.after_cursor + state.suggestion)
                if to_erase > 0:
                    stdout.write(color.Fore.DEFAULT + color.Back.DEFAULT + ' ' * to_erase)
                    cursor_backward(to_erase)

                # Move cursor to the correct position
                set_cursor_attributes(cursor_height, True)
                cursor_backward(len(state.after_cursor + state.suggestion))

            # Bell if a notification is pending
            if state.bell:
                console.visual_bell()
                state.bell = False

            # Prepare new input state
            state.step_line()

            # Read and process a keyboard event
            rec = read_input()
            select = auto_select or is_shift_pressed(rec)

            # Will be overridden if Shift-PgUp/Dn is pressed
            force_repaint = not is_control_only(rec)

            #print('\n\n', rec.KeyDown, rec.Char, rec.VirtualKeyCode, rec.ControlKeyState, '\n\n')
            if is_ctrl_pressed(rec) and not is_alt_pressed(rec):  # Ctrl-Something
                if rec.Char == chr(4):                  # Ctrl-D
                    if state.before_cursor + state.after_cursor == '':
                        internal_exit('\r\nBye!')
                    else:
                        state.handle(ActionCode.ACTION_DELETE)
                elif rec.Char == chr(31):                   # Ctrl-_
                    state.handle(ActionCode.ACTION_UNDO_EMACS)
                    auto_select = False
                elif rec.VirtualKeyCode == 75:          # Ctrl-K
                    state.handle(ActionCode.ACTION_KILL_EOL)
                elif rec.VirtualKeyCode == 32:          # Ctrl-Space
                    auto_select = True
                    state.reset_selection()
                elif rec.VirtualKeyCode == 71:          # Ctrl-G
                    if scrolling:
                        scrolling = False
                    else:
                        state.handle(ActionCode.ACTION_ESCAPE)
                        update_history('add', state.history.list[-1],
                                       pycmd_data_dir + '/history',
                                       save_history_limit)
                        auto_select = False
                elif rec.VirtualKeyCode == 82:          # Ctrl-R
                    w = Window(state.history.list, pattern=re.compile('(.*)$'),
                               height=optimal_window_height())
                    w.display()
                    w.filter = state.history.filter if state.history.filter else state.before_cursor + state.after_cursor
                    action, selection = w.interact(default_selection_last=True, can_zap=True)
                    if action == 'select':
                        state.before_cursor = selection
                        state.after_cursor = ''
                        state.reset_selection()
                        state.history.reset()
                    elif action == 'zap':
                        state.zap(selection)
                        update_history('remove', selection, pycmd_data_dir + '\\history', save_history_limit)
                elif rec.VirtualKeyCode == 65:          # Ctrl-A
                    state.handle(ActionCode.ACTION_HOME, select)
                elif rec.VirtualKeyCode == 69:          # Ctrl-E
                    state.handle(ActionCode.ACTION_END, select)
                elif rec.VirtualKeyCode == 66:          # Ctrl-B
                    state.handle(ActionCode.ACTION_LEFT, select)
                elif rec.VirtualKeyCode == 70:          # Ctrl-F
                    state.handle(ActionCode.ACTION_RIGHT, select)
                elif rec.VirtualKeyCode == 80:          # Ctrl-P
                    state.handle(ActionCode.ACTION_PREV)
                elif rec.VirtualKeyCode == 78:          # Ctrl-N
                    state.handle(ActionCode.ACTION_NEXT)
                elif rec.VirtualKeyCode == 37:          # Ctrl-Left
                    state.handle(ActionCode.ACTION_LEFT_WORD, select)
                elif rec.VirtualKeyCode == 39:          # Ctrl-Right
                    state.handle(ActionCode.ACTION_RIGHT_WORD, select)
                elif rec.VirtualKeyCode == 46:          # Ctrl-Delete
                    state.handle(ActionCode.ACTION_DELETE_WORD)
                elif rec.VirtualKeyCode == 67:          # Ctrl-C
                    # The Ctrl-C signal is caught by our custom handler, and a
                    # synthetic keyboard event is created so that we can catch
                    # it here
                    if state.get_selection() != '':
                        state.handle(ActionCode.ACTION_COPY)
                    else:
                        state.handle(ActionCode.ACTION_ESCAPE)
                    auto_select = False
                elif rec.VirtualKeyCode == 88:          # Ctrl-X
                    state.handle(ActionCode.ACTION_CUT)
                    auto_select = False
                elif rec.VirtualKeyCode == 87:          # Ctrl-W
                    state.handle(ActionCode.ACTION_CUT)
                    auto_select = False
                elif rec.VirtualKeyCode == 86:          # Ctrl-V
                    state.handle(ActionCode.ACTION_PASTE)
                    auto_select = False
                elif rec.VirtualKeyCode == 89:          # Ctrl-Y
                    state.handle(ActionCode.ACTION_PASTE)
                    auto_select = False
                elif rec.VirtualKeyCode == 8:           # Ctrl-Backspace
                    state.handle(ActionCode.ACTION_BACKSPACE_WORD)
                elif rec.VirtualKeyCode == 90:  
                    if not is_shift_pressed(rec):       # Ctrl-Z
                        state.handle(ActionCode.ACTION_UNDO)
                    else:                               # Ctrl-Shift-Z
                        state.handle(ActionCode.ACTION_REDO)
                    auto_select = False
                elif rec.Char == chr(10):                # Ctrl-Enter
                    state.handle(ActionCode.ACTION_END)          # Emulate "End"
                    write_input(rec.VirtualKeyCode, chr(13), 0)  # followed by "Enter"
                    continue
            elif is_alt_pressed(rec) and not is_ctrl_pressed(rec):      # Alt-Something
                if rec.VirtualKeyCode in [37, 39] + list(range(49, 59)):
                    if state.before_cursor + state.after_cursor == '':  # Dir history
                        state.reset_prev_line()
                        if rec.VirtualKeyCode == 37:            # Alt-Left
                            dir_hist.go_left()
                            apply_cwd()
                            break
                        elif rec.VirtualKeyCode == 39:          # Alt-Right     
                            dir_hist.go_right()
                            apply_cwd()
                            break
                        state.prev_prompt = state.prompt
                        state.prompt = appearance.prompt()
                        update_dir_history()
                    else:
                        if rec.VirtualKeyCode == 37:            # Alt-Left
                            state.handle(ActionCode.ACTION_LEFT_WORD, select)
                        elif rec.VirtualKeyCode == 39:          # Alt-Right
                            state.handle(ActionCode.ACTION_RIGHT_WORD, select)
                elif rec.VirtualKeyCode == 38:          # Alt-Up
                    if state.before_cursor + state.after_cursor == '':
                        os.chdir('..')
                        dir_hist.visit_cwd()
                        apply_cwd()
                        break
                elif rec.VirtualKeyCode == 66:          # Alt-B
                    state.handle(ActionCode.ACTION_LEFT_WORD, select)
                elif rec.VirtualKeyCode == 70:          # Alt-F
                    state.handle(ActionCode.ACTION_RIGHT_WORD, select)
                elif rec.VirtualKeyCode == 80:          # Alt-P
                    state.handle(ActionCode.ACTION_PREV)
                elif rec.VirtualKeyCode == 78:          # Alt-N
                    state.handle(ActionCode.ACTION_NEXT)
                elif rec.VirtualKeyCode == 68:          # Alt-D
                    if state.before_cursor + state.after_cursor == '':
                        w = Window(dir_hist.locations, pattern=re.compile('(.*)$'),
                                   height=optimal_window_height())
                        w.display()
                        action, selection = w.interact(initial_index=dir_hist.index)
                        if action == 'select' and selection:
                            dir_hist.jump(selection)
                            apply_cwd()
                            state.prev_prompt = state.prompt
                            state.prompt = appearance.prompt()
                            update_dir_history()
                            break
                    else:
                        state.handle(ActionCode.ACTION_DELETE_WORD) 
                elif rec.VirtualKeyCode == 87:          # Alt-W
                    state.handle(ActionCode.ACTION_COPY)
                    state.reset_selection()
                    auto_select = False
                elif rec.VirtualKeyCode == 46:          # Alt-Delete
                    state.handle(ActionCode.ACTION_DELETE_WORD)
                elif rec.VirtualKeyCode == 8:           # Alt-Backspace
                    state.handle(ActionCode.ACTION_BACKSPACE_WORD)
                elif rec.VirtualKeyCode == 191:
                    state.handle(ActionCode.ACTION_EXPAND)
            elif is_ctrl_pressed(rec) and is_alt_pressed(rec) and rec.VirtualKeyCode == 75: # Ctrl-Alt-K
                line = state.before_cursor + state.after_cursor
                state.handle(ActionCode.ACTION_ZAP)
                update_history('remove', line, pycmd_data_dir + '\\history', save_history_limit)
            elif is_shift_pressed(rec) and rec.VirtualKeyCode == 33:    # Shift-PgUp
                (_, t, _, b) = get_viewport()
                scroll_buffer(t - b + 2)
                scrolling = True
                force_repaint = False
            elif is_shift_pressed(rec) and rec.VirtualKeyCode == 34:    # Shift-PgDn
                (_, t, _, b) = get_viewport()
                scroll_buffer(b - t - 2)
                scrolling = True
                force_repaint = False
            elif is_shift_pressed(rec) and rec.VirtualKeyCode == 114:   # Shift-F3
                state.handle(ActionCode.ACTION_SEARCH_LEFT)
            elif is_shift_pressed(rec) and rec.VirtualKeyCode == 38:    # Shift-Up
                state.handle(ActionCode.ACTION_SELECT_UP)
            elif is_shift_pressed(rec) and rec.VirtualKeyCode == 40:    # Shift-Down
                state.handle(ActionCode.ACTION_SELECT_DOWN)
            else:                                       # Clean key (no modifiers)
                if rec.Char == chr(0):                  # Special key (arrows and such)
                    if rec.VirtualKeyCode == 37:        # Left arrow
                        state.handle(ActionCode.ACTION_LEFT, select)
                    elif rec.VirtualKeyCode == 39:      # Right arrow
                        state.handle(ActionCode.ACTION_RIGHT, select)
                    elif rec.VirtualKeyCode == 36:      # Home
                        state.handle(ActionCode.ACTION_HOME, select)
                    elif rec.VirtualKeyCode == 35:      # End
                        state.handle(ActionCode.ACTION_END, select)
                    elif rec.VirtualKeyCode == 38:      # Up arrow
                        state.handle(ActionCode.ACTION_PREV)
                    elif rec.VirtualKeyCode == 40:      # Down arrow
                        state.handle(ActionCode.ACTION_NEXT)
                    elif rec.VirtualKeyCode == 46:      # Delete
                        state.handle(ActionCode.ACTION_DELETE)
                    elif rec.VirtualKeyCode == 45:      # Insert
                        state.handle(ActionCode.ACTION_TOGGLE_OVERWRITE)
                    elif rec.VirtualKeyCode == 114:     # F3:
                        state.handle(ActionCode.ACTION_SEARCH_RIGHT)


                elif rec.Char == chr(13):               # Enter
                    state.history.reset()
                    if (state.before_cursor + state.after_cursor).strip() == '':
                        if sys.platform == 'linux':
                            debug('Empty line input_processed.set')
                            pty_control.input_processed.set()
                    break
                elif rec.Char == chr(27):               # Esc
                    if scrolling:
                        scrolling = False
                    else:
                        state.handle(ActionCode.ACTION_ESCAPE)
                        auto_select = False
                elif rec.Char == '\t':                  # Tab
                    set_cursor_attributes(cursor_height, False)
                    tokens = tokenize(state.before_cursor)
                    if ends_in_env_var(tokens[-1]):
                        (completed, suggestions) = complete_env_var(state.before_cursor)
                    elif has_wildcards(tokens[-1]):
                        (completed, suggestions)  = complete_wildcard(state.before_cursor)
                    else:
                        (completed, suggestions)  = complete_file(state.before_cursor)

                    stdout.write(state.after_cursor + ' ' * len(state.suggestion))
                    cursor_backward(len(state.suggestion) + len(state.after_cursor) + len(state.before_cursor))
                    state.handle(ActionCode.ACTION_COMPLETE, completed)
                    stdout.write(state.before_cursor + state.after_cursor)
                    stdout.write(appearance.colors.suggestion + state.suggestion + color.Fore.DEFAULT + color.Back.DEFAULT + appearance.colors.text)
                    cursor_backward(len(state.after_cursor) + len(state.suggestion))
                    set_cursor_attributes(cursor_height, True)
                    state.step_line()

                    # Show multiple completions if available
                    if not suggestions:
                        # No completion possible, require notification
                        state.bell = True
                    elif len(suggestions) > 1:
                        # Multiple completions possible
                        path_sep = '/' if '/' in expand_env_vars(tokens[-1]) else os.sep
                        if tokens[-1]:
                            # Tokenize again in case the original line has been appended to
                            tokens = tokenize(completed.rstrip(' ').rstrip(path_sep))
                        token = tokens[-1].replace('"', '')

                        if has_wildcards(tokens[-1]):
                            # Substring matching wildcards will be printed in a different color
                            (_, _, prefix) = token.rpartition(path_sep)
                        else:
                            # Length of the common prefix will be printed in a different color
                            prefix = find_common_prefix(state.before_cursor, suggestions)
                        pattern = wildcard_to_regex(prefix + '*')

                        if behavior.completion_mode == 'bash':
                            w = Window(suggestions, pattern)
                            num_screens = 1.0 * w.height / (get_viewport()[3] - get_viewport()[1])
                            if num_screens >= 0.9:
                                # We ask for confirmation before displaying many completions
                                (c_x, c_y) = get_cursor()
                                offset_from_bottom = get_buffer_size()[1] - c_y
                                message = ' Scroll ' + str(int(round(num_screens))) + ' screens? [Tab] '
                                stdout.write('\r\n' + message)
                                stdout.flush()
                                if sys.platform == 'linux':
                                    debug('bash-completion-confirm input_processed.set')
                                    pty_control.input_processed.set()
                                rec = read_input()
                                move_cursor(c_x, get_buffer_size()[1] - offset_from_bottom)
                                stdout.write('\r\n' + ' ' * len(message))
                                move_cursor(c_x, get_buffer_size()[1] - offset_from_bottom)
                                if rec.Char != '\t':
                                    if not ord(rec.Char) in [0, 8, 13, 27]:
                                        state.handle(ActionCode.ACTION_INSERT, rec.Char)
                                    state.reset_prev_line()
                                    if sys.platform == 'linux':
                                        debug('bash-completion-nextchar input_processed.set')
                                        pty_control.input_processed.set()
                                    continue
                            w.display()
                            state.reset_prev_line()
                        else:
                            w = Window(suggestions, pattern, height=optimal_window_height())
                            w.display()
                            w.reset_cursor()

                            if sys.platform == 'linux':
                                debug('zsh completion input_processed.set')
                                pty_control.input_processed.set()
                            while True:
                                r = read_input()
                                if not is_control_only(r):
                                    break
                            if r.Char == chr(0) and r.VirtualKeyCode == 40 or is_ctrl_pressed(r) and r.VirtualKeyCode == 78:
                                stdout.write(state.after_cursor + ' ' * len(state.suggestion))  # Erase suggestion
                                cursor_backward(len(state.after_cursor) + len(state.suggestion))
                                action, selection = w.interact()
                                if action == 'select' and selection:
                                    orig_last_token = tokenize(state.before_cursor)[-1]

                                    # Replace initial completion prefix with selection,
                                    # add quotes and slashes as needed
                                    pos = state.before_cursor.lower().rfind(prefix.lower())
                                    state.before_cursor = (state.before_cursor[:pos]
                                                           + selection
                                                           + state.before_cursor[pos + len(prefix):])

                                    # Ensure proper terminating (%, quotes, whitespaces)
                                    if orig_last_token.count('%') % 2 == 1:
                                        state.before_cursor += '%'
                                    if orig_last_token.startswith('"'):
                                        state.before_cursor += '"'
                                    elif ' ' in selection:
                                        pos = state.before_cursor.rfind(orig_last_token)
                                        state.before_cursor = state.before_cursor[:pos] + '"' + state.before_cursor[pos:] + '"'
                                    if (not selection.endswith(path_sep)
                                        and not orig_last_token.count('%') % 2 == 1
                                        and not completed.endswith(' ')):
                                        state.before_cursor += ' '
                                    state.reset_selection()
                                    state.update_suggestion()
                            else:
                                write_input(r.VirtualKeyCode, r.Char, r.ControlKeyState)
                                w.erase()
                                if sys.platform == 'linux':
                                    debug('zsh completion writeback input_available.set')
                                    pty_control.input_available.set()
                                continue
                        set_cursor_attributes(cursor_height, True)
                elif rec.Char == chr(8):                # Backspace
                    state.handle(ActionCode.ACTION_BACKSPACE)
                else:                                   # Regular character
                    tokens_before = tokenize(state.before_cursor)
                    state.handle(ActionCode.ACTION_INSERT, rec.Char)
                    tokens_after = tokenize(state.before_cursor)
                    
            if sys.platform == 'linux':
                debug('Step input_processed.set')
                pty_control.input_processed.set()


        # Done reading line, now execute
        stdout.write(state.after_cursor)        # Move cursor to the end
        stdout.write(' ' * len(state.suggestion))  # Erase suggestion
        cursor_backward(len(state.suggestion))

        line = (state.before_cursor + state.after_cursor).strip()
        tokens = tokenize(line)
        if tokens == [] or tokens[0] == '':
            continue
        else:
            print()
            if not is_pure_cd(tokens):
                dir_hist.keep = True
            run_command(tokens)

        # Add to history
        state.history.add(line)
        update_history('add', state.history.list[-1],
                       pycmd_data_dir + '/history',
                       save_history_limit)

        # Add to dir history
        dir_hist.visit_cwd()
        update_dir_history()

        # Update default color
        color.update()


def internal_cd(args):
    """The internal CD command"""
    try:
        if len(args) > 0 and args[0].lower() == "/d":
            # cmd.exe requires `/d` when changing volumes; we just ignore it
            args.pop(0)
        if len(args) == 0:
            os.chdir(expand_env_vars('~'))
        else:
            if len(args) == 1:
                target = args[0]
            else:
                target = " ".join(args)
            if target != '\\' and target[1:] != ':\\':
                target = target.rstrip('\\')
            target = expand_env_vars(target.strip('"').strip(' '))
            os.chdir(target)
        os.environ['ERRORLEVEL'] = '0'
    except FileNotFoundError as error:
        stderr.write(f'The system cannot find the path specified: {error.filename}\n')
        os.environ['ERRORLEVEL'] = '1'
    except PermissionError as error:
        stderr.write(f'Access is denied: {error.filename}\n')
        os.environ['ERRORLEVEL'] = '1'
    except OSError as error:
        stderr.write(str(error).replace('\\\\', '\\') + '\n')
        os.environ['ERRORLEVEL'] = '1'
    os.environ['CD'] = os.getcwd()


def apply_cwd():
    if sys.platform == 'linux':
        run_command(['cd', f'"{os.getcwd()}"', ';', '(exit %s)' % os.environ['ERRORLEVEL']])


def internal_exit(message = ''):
    """The EXIT command, with an optional goodbye message"""
    deinit()
    if ((not behavior.quiet_mode) and message != ''):
        print(message)
    if sys.platform == 'linux':
        run_command(['exit'])
    else:
        sys.exit()


def run_command(tokens):
    if sys.platform == 'linux':
        run_command_linux(tokens)
    else:
        run_command_win(tokens)


def run_command_linux(tokens):
    #print('Running', tokens)
    pty_control.command_to_run = ' '.join(tokens) + '\n'
    pty_control.pass_through = True
    debug('run_command input_processed.set')
    pty_control.input_processed.set()
    if tokens == ['exit']:
        time.sleep(0.5)
        deinit()
        os.system('reset -I')
        sys.exit()

    while pty_control.pass_through:
        time.sleep(0.01)
    # print(f'Captured[{captured_prompt}]')
    curdir, exit_code = pty_control.captured_prompt.split('|')
    os.chdir(curdir)
    os.environ['ERRORLEVEL'] = exit_code

    # Update environment and state
    new_environ = {}
    env_file = open(tmpfile, 'r')
    for line in [l for l in env_file.readlines() if not l.isspace()]:
        [variable, value] = line.split('=', 1)
        value = value.rstrip('\n ')
        new_environ[variable] = value
    env_file.close()
    if new_environ != {}:
        for variable in os.environ.keys():
            if not variable in new_environ.keys() and variable != 'ERRORLEVEL':
                del os.environ[variable]
        for variable in new_environ:
            if variable != 'ERRORLEVEL':
                os.environ[variable] = new_environ[variable]


def run_command_win(tokens):
    """Execute a command line (treat internal and external appropriately"""
    import win32console, win32gui, win32con
    
    # Inline %ERRORLEVEL%
    if behavior.delayed_expansion:
        tokens = [t.replace('%ERRORLEVEL%', os.environ['ERRORLEVEL']) for t in tokens]

    # Cleanup environment
    for var in pseudo_vars:
        if var in os.environ.keys():
            del os.environ[var]

    if tokens[0] == 'exit':
        internal_exit('Bye!')
    elif is_pure_cd(tokens):
        # This is a single CD command -- use our custom, more handy CD
        internal_cd([unescape(t) for t in tokens[1:]])
    else:
        # cx_freeze calls SetDllDirectory() to exert control over the
        # loading of DLLs by imported packages; this PROPAGATES TO
        # SUBPROCESSES and can therefore influence the behavior of
        # programs spawned by PyCmd. Here we reset the DLL search
        # behavior to the default; we will restore it after executing
        # the command
        try:
            orig_dll_dir = win32api.GetDllDirectory()
        except:
            orig_dll_dir = None
        win32api.SetDllDirectory(None)

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

            if not ext or ext in exec_extensions:
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
                        s = u' '.join([expand_tilde(t) for t in tokens])
                        subprocess.Popen(s, shell=True)
                        os.environ['ERRORLEVEL'] = '0'
                        win32api.SetDllDirectory(orig_dll_dir)
                        return

        # Regular (external) command
        start_time = time.time()
        run_in_cmd(tokens)
        win32api.SetDllDirectory(orig_dll_dir)
        console_window = win32console.GetConsoleWindow()
        if win32gui.GetForegroundWindow() != console_window and time.time() - start_time > 15:
            # If the window is inactive, flash after long t1asks
            win32gui.FlashWindowEx(console_window, win32con.FLASHW_ALL, 3, 750)


def is_pure_cd(tokens):
    return tokens[0].lower() == 'cd' and [t for t in tokens if t in sep_tokens] == []


def run_in_cmd(tokens):
    line_sanitized = ''
    for token in tokens:
        token_sane = expand_tilde(token)
        if token_sane != '\\' and token_sane[1:] != ':\\':
            token_sane = token_sane.rstrip('\\')
        if token_sane.count('"') % 2 == 1:
            token_sane += '"'
        if token_sane.count('"') > 0 and behavior.delayed_expansion:
            # Escape certain special characters in quptes to compensate for our awkward
            # command execution mechanism (based on cmd /C)
            token_sane = escape_special_chars_in_quotes(token_sane)
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

    # Run command
    if line_sanitized != '':
        command = '"'
        global pushd_stack
        if pushd_stack:
            (first_dir, *rest) = (*pushd_stack, os.getcwd())
            command += 'cd /d "' + first_dir + '"'
            for d in rest:
                command += '& pushd "' + d + '"'
            command += ' & '
        command += line_sanitized
        command += ' &set > "' + tmpfile + '"'
        if behavior.delayed_expansion:
            for var in pseudo_vars:
                command += ' & echo ' + var + '="!' + var + '!" >> "' + tmpfile + '"'
            command = '%COMSPEC% /V:ON /c ' + command
        else:
            for var in pseudo_vars:
                command += ' & echo ' + var + '="%' + var + '%" >> "' + tmpfile + '"'
            command += '& <nul (set /p xxx=CD=) >>"' + tmpfile + '" & cd >>"' + tmpfile + '"'
        command += '& echo ===PUSHD STACK BEGIN=== >> ' + '"' + tmpfile + '"'
        command += '& pushd >> ' + '"' + tmpfile + '"'
        command += '& echo ===PUSHD STACK END=== >> ' + '"' + tmpfile + '"'
        command += '"'
        os.system(command)

    # Update environment and state
    new_environ = {}
    with open(tmpfile, 'r') as env_file:
        lines = [l.rstrip('\n ') for l in env_file.readlines() if not l.isspace()]

    # parse env
    i = 0
    while i < len(lines):
        if lines[i] == "===PUSHD STACK BEGIN===":
            break
        (variable, value) = lines[i].split('=', 1)
        if variable in pseudo_vars:
            value = value.strip('"')
        new_environ[variable] = value
        i += 1

    # parse pushd stack
    pushd_stack = []
    i += 1
    while i < len(lines):
        if lines[i] == "===PUSHD STACK END===":
            break
        pushd_stack.append(lines[i])
        i += 1

    if new_environ != {}:
        for variable in os.environ.keys():
            if not variable in new_environ.keys() \
                   and sorted(new_environ.keys()) != sorted(pseudo_vars):
                del os.environ[variable]
        for variable in new_environ:
            os.environ[variable] = new_environ[variable]
    cd = os.environ['CD']
    os.chdir(cd.encode(sys.getfilesystemencoding()))


def signal_handler(signum, frame):
    """
    Signal handler that catches SIGINT and emulates the Ctrl-C
    keyboard combo
    """
    if signum == signal.SIGINT:
        # Emulate a Ctrl-C press
        write_input(67, u'c', 0x0008)

def optimal_window_height():
    _, viewport_top, _, viewport_bottom  = get_viewport()
    window_height = viewport_bottom - get_cursor()[1] - 1
    if window_height < (viewport_bottom - viewport_top) // 3:
        window_height = (viewport_bottom - viewport_top) // 3
    return window_height


def update_history(action, line, filename, length):
    """
    Append/remove a line to/from a history file.  
    When adding, if the line was already present in the file, we move it to
    the end. The resulting file is then truncated to the specified number of 
    lines.
    """
    if os.path.isfile(filename):
        # Read previously saved history and merge with current
        history_file = codecs.open(filename, 'r', 'utf8', 'replace')
        history_to_save = [l.rstrip(u'\n') for l in history_file.readlines()]
        history_file.close()
        if line in history_to_save:
            history_to_save.remove(line)
        if action == 'add':
            history_to_save.append(line)
    else:
        # No previous history, save current (only if adding)
        history_to_save = [line] if action == 'add' else []

    if len(history_to_save) > length:
        history_to_save = history_to_save[-length :]    # Limit history file

    # Write merged history to history file
    history_file = codecs.open(filename, 'w', 'utf8')
    history_file.writelines([l + u'\n' for l in history_to_save])
    history_file.close()


def read_history(filename):
    """
    Read and return a list of lines from a history file
    """
    if os.path.isfile(filename):
        history_file = codecs.open(filename, 'r', 'utf8', 'replace')
        history = [line.rstrip(u'\n\r') for line in history_file.readlines()]
        history_file.close()
    else:
        print('Warning: Can\'t open ' + os.path.basename(filename) + '!')
        history = []
    return history


def update_dir_history():
    update_history('add',
                   dir_hist.locations[-1],
                   pycmd_data_dir + '/dir_history',
                   dir_hist.max_len)


def print_usage():
    """Print usage information"""
    print('Usage:')
    print('\t PyCmd [-i script] [-t title] ( [-c command] | [-k command] | [-h] )')
    print()
    print('\t\t-c command \tRun command, then exit')
    print('\t\t-k command \tRun command, then continue to the prompt')
    print('\t\t-t title \tShow title in window caption')
    print('\t\t-i script \tRun additional init/config script')
    print('\t\t-q\t\tQuiet (suppress messages)')
    print('\t\t-h \t\tShow this help')
    print()
    print('Note that you can use \'/\' instead of \'-\', uppercase instead of ')
    print('lowercase and \'/?\' instead of \'-h\'')

    
# cx_freeze sometimes messes this (no idea why...)
if __name__ == 'pycmd__main__':
    __name__ = '__main__'

# Entry point
if __name__ == '__main__':
    try:
        init()
        main()
    except Exception as e:        
        report_file_name = (pycmd_data_dir
                            + '/crash-' 
                            + time.strftime('%Y%m%d_%H%M%S') 
                            + '.log')
        print('\n')
        print('************************************')
        print('PyCmd has encountered a fatal error!')
        print()
        report_file = open(report_file_name, 'w')
        traceback.print_exc(file=report_file)
        report_file.close()
        traceback.print_exc()
        print()
        print('Crash report written to:\n  ' + report_file_name)
        print()
        if sys.platform == 'win32':
            print('Press any key to exit... ')
            print('************************************')
            read_input()
        internal_exit()
