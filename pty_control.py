import sys, os, threading, time, tty, pty, fcntl, array, termios

input_processed = False
command_to_run = None
pass_through = True
MARKER = '_M' + 'ARKE' + 'R_'
MARKER_BYTES = bytearray(MARKER, 'utf-8')
marker_acc = []
input_buffer = []
captured_prompt = None


def read_stdin(fd):
    global input_processed, pass_through
    ch = os.read(fd, 1)
    if pass_through:
        return ch
    else:
        input_processed = False
        input_buffer.append(ch[0])
        while not input_processed:
            time.sleep(0)
        if command_to_run:
            return bytearray(command_to_run, 'utf-8')
        else:
            return bytearray(chr(0), 'utf-8')

def read_shell(fd):
    global command_to_run, pass_through, marker_buffer, marker_acc, captured_prompt

    if command_to_run:
        # ensure terminal dimensions match the real terminal
        #
        # TODO this is too late for bash to correctly expand $LINES
        # and $COLUMNS in the *current* command (works fine for other
        # commands, thoug). Ideally we should trigger this update at
        # an eariler time.
        buf = array.array('h', [0, 0, 0, 0])
        fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, buf)

        # bash outputs the command; we swallow it
        os.read(fd, len(command_to_run) - 1)
        command_to_run = None
        marker_acc = []
        return bytearray(chr(0), 'utf-8')
    else:
        if pass_through:
            # Command is running, pass output through until a MARKER is detected
            # TODO marker_acc and captured_prompt should be turned into bytearrays for efficiency
            ch = os.read(fd, 1)[0]
            marker_acc.append(ch)
            while len(marker_acc) < len(MARKER_BYTES) and ch == MARKER_BYTES[len(marker_acc) - 1]:
                ch = os.read(fd, 1)[0]
                marker_acc.append(ch)

            if len(marker_acc) == len(MARKER_BYTES):
                # first MARKER (begin) has been detected; search for the next one (end)
                captured_prompt = []
                while captured_prompt[-len(MARKER_BYTES):] != list(MARKER_BYTES):
                    ch = os.read(fd, 1)[0]
                    captured_prompt.append(ch)

                captured_prompt = bytearray(captured_prompt[:-len(MARKER_BYTES)]).decode('utf-8')
                pass_through = False
                marker_acc = []
                return bytearray(chr(0), 'utf-8')
            else:
                # this is not the MARKER, return the accumulated bytes
                bytes = bytearray(marker_acc)
                marker_acc = []
                return bytes
        else:
            return os.read(fd, 1)

        
def start():
    # Direct character processing
    tty.setcbreak(sys.stdin)
    os.environ['PS1'] = MARKER + r'$PWD|$?' + MARKER
    t = threading.Thread(group=None,
                         target=(lambda: pty.spawn(['/bin/bash', '--norc'],
                                               master_read=read_shell,
                                               stdin_read=read_stdin)))
    t.start()


