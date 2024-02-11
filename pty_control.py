import sys, os, threading, tty, pty, fcntl, array, termios, tempfile
from common import debug

input_processed = threading.Event()
input_available = threading.Event()
command_to_run = None
pass_through = True
command_completed = threading.Event()
terminated = False

# The "interpreted" MARKER (i.e. the string that bash will show when printing the
# prompt) must be different from the "raw" MARKER, i.e. the actual value of the
# PS1 variable; otherwise echoing $PS1 will trick the prompt detection mechanism
# in read_shell()
MARKER_BASE = '_MARKER_'
MARKER_RAW = r'\036' + MARKER_BASE
MARKER = '\036' + MARKER_BASE
MARKER_BYTES = bytearray(MARKER, 'utf-8')
output_acc = bytearray()
marker_acc = bytearray()
no_buffering = False
input_buffer = []
captured_prompt = None


def read_stdin(fd):
    global pass_through
    debug('read_stdin os.read')
    ch = os.read(fd, 1)
    if pass_through:
        return ch
    else:
        input_buffer.append(ch[0])
        debug('read_stdin input_available.set')
        input_available.set()
        debug('read_stdin input_processed.wait')
        input_processed.wait()
        debug('read_stdin got')
        input_processed.clear()
        if command_to_run:
            return bytearray(command_to_run, 'utf-8')
        else:
            return bytearray(chr(0), 'utf-8')

def read_shell(fd):
    global command_to_run, pass_through, captured_prompt, output_acc, marker_acc, no_buffering

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

        # bash outputs the command; we swallow it (incl. '\r\n')
        remaining = len(command_to_run) + 1
        while remaining > 0:
            remaining -= len(os.read(fd, remaining))
        command_to_run = None
        output_acc = bytearray()
        marker_acc = bytearray()
        no_buffering = False
        return bytearray(chr(0), 'utf-8')
    else:
        if pass_through:
            # Command is running, pass output through until a MARKER is detected
            while True:
                ch = os.read(fd, 1)
                if ch[0] == MARKER_BYTES[len(marker_acc)]:
                    # this could still be the marker, push to marker accumulator
                    marker_acc.extend(ch)
                    if len(marker_acc) == len(MARKER_BYTES):
                        # first MARKER (begin) has been detected; search for the next one (end)
                        capture_buffer = bytearray()
                        while capture_buffer[-len(MARKER_BYTES):] != MARKER_BYTES:
                            ch = os.read(fd, 1)
                            if ch[0] == ord('\r'):
                                # When the prompt is longer than $COLUMNS, some versions of bash re-print
                                # the first overflowing character preceded by '\r'
                                os.read(fd, 1)
                                continue
                            capture_buffer.extend(ch)
                        captured_prompt = capture_buffer[:-len(MARKER_BYTES)].decode('utf-8')
                        pass_through = False
                        command_completed.set()
                        marker_acc = bytearray()
                        no_buffering = False
                        output = bytes(output_acc)
                        output_acc = bytearray()
                        return output + bytes(chr(0), 'utf-8')
                else:
                    # we no longer match a marker prefix, move whatever we might have matched already
                    # into the output accumulator
                    output_acc.extend(marker_acc)
                    output_acc.extend(ch)
                    marker_acc = bytearray()
                    
                    if ch[0] == 27:
                        # This might be an escape sequence, we must disable buffering for this run
                        no_buffering = True
                    elif ch[0] == ord('\n'):
                        # We encountered a newline, so we assume any escape sequence is by now completed
                        no_buffering = False
                        
                    if ch[0] == ord('\n') or no_buffering:
                        # return the content of the output accumulator to the tty
                        output = bytes(output_acc)
                        output_acc = bytearray()
                        return output + bytes(chr(0), 'utf-8')
        else:
            return os.read(fd, 1)

        
def start(env_dump_file):
    # Direct character processing
    tty.setcbreak(sys.stdin)
    ps1 = MARKER_RAW + r'$PWD|$?' + MARKER_RAW

    # We make the temp file global, otherwise it will be deleted when
    # this function ends -- which could be before beash gets a chance
    # to read it!
    global rc      
    try:
        rc = tempfile.NamedTemporaryFile()
        rc.write(open(os.path.expanduser('~/.bashrc'), 'rb').read())
        rc.write(f"PS1='{ps1}'\n".encode('utf-8'))
        rc.write(f'PROMPT_COMMAND="printenv > {env_dump_file}"\n'.encode('utf-8'))
        rc.write('HISTCONTROL=ignorespace\n'.encode('utf-8'))
        rc.write("bind 'set enable-bracketed-paste off'\n".encode('utf-8'))
        rc.flush()
    except OSError as e:
        pass

    def run_shell():
        global terminated
        terminated = False
        pty.spawn(['/bin/bash', '--rcfile', rc.name],
                  master_read=read_shell,
                  stdin_read=read_stdin)
        terminated = True
        command_completed.set()

    t = threading.Thread(group=None, target=run_shell)
    t.start()
