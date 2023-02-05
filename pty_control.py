import sys, os, threading, time, tty, pty

input_processed = False
command_to_run = None
pass_through = True
MARKER = 'MARKER'
marker_buffer = bytearray(len(MARKER))
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
            time.sleep(0.1)
        if command_to_run:
            return bytearray(command_to_run, 'utf-8')
        else:
            return bytearray(chr(0), 'utf-8')

def read_shell(fd):
    global command_to_run, pass_through, marker_buffer, captured_prompt
    if command_to_run:
        os.read(fd, len(command_to_run) - 1)
        command_to_run = None
        return bytearray(chr(0), 'utf-8')
    else:
        ch = os.read(fd, 1)
        if pass_through:
            discarded = marker_buffer[0:1]
            marker_buffer.pop(0)
            marker_buffer += ch
            if ''.join(marker_buffer.decode('utf-8')) == MARKER:
                captured_prompt = ''
                while not captured_prompt.endswith(MARKER):
                    captured_prompt += os.read(fd, 1).decode('utf-8')
                captured_prompt = captured_prompt[:-len(MARKER)]
                pass_through = False
                marker_buffer = bytearray(len(MARKER))
            return discarded
        else:
            return ch

        
def start():
    # Direct character processing
    tty.setcbreak(sys.stdin)
    os.environ['PS1'] = MARKER + r'$PWD|$?' + MARKER
    t = threading.Thread(group=None,
                         target=(lambda: pty.spawn(['/bin/bash', '--norc'],
                                               master_read=read_shell,
                                               stdin_read=read_stdin)))
    t.start()


