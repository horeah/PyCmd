#
# Functions for manipulating the console using ANSI terminal sequences
#
from itertools import chain
from functools import reduce
from dataclasses import dataclass
import ctypes, sys, locale, time
from ctypes import Structure, Union, c_int, c_long, c_char, c_wchar, c_short, pointer, byref
from ctypes.wintypes import BOOL, WORD, DWORD
from pty_control import pty_control
from .console_common import *

# These are taken from the win32console
LEFT_ALT_PRESSED = 0x0002
LEFT_CTRL_PRESSED = 0x0008
RIGHT_ALT_PRESSED = 0x0001
RIGHT_CTRL_PRESSED = 0x0004
SHIFT_PRESSED = 0x0010

@dataclass
class PyINPUT_RECORDType:
    KeyDown: bool = False
    VirtualKeyCode: int = 0
    Char: str = '\0'
    ControlKeyState: int = 0


def set_text_attributes(color):
    """Set foreground/background RGB components for the text to write"""
    ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, color)

def get_buffer_attributes(x, y, n):
    """Get the fg/bg/attributes for the n chars in the buffer starting at (x, y)"""
    colors = (n * WORD)()
    coord = COORD(x, y)
    read = DWORD(0)
    sys.__stdout__.flush()
    ctypes.windll.kernel32.ReadConsoleOutputAttribute(stdout_handle, colors, n, coord, pointer(read))
    return colors

def set_buffer_attributes(x, y, colors):
    """Set the fg/bg attributes for the n chars in the the buffer starting at (x, y)"""
    coord = COORD(x, y)
    written = DWORD(0)
    ctypes.windll.kernel32.WriteConsoleOutputAttribute(stdout_handle, colors, len(colors), coord, pointer(written))

def visual_bell():
    """Flash the screen for brief moment to notify the user"""
    l, t, r, b = get_viewport()
    count = (r - l + 1) * (b - t + 1)
    colors = get_buffer_attributes(l, t, count)
    reverted_colors = (count * WORD)(*tuple([c ^ BACKGROUND_BRIGHT for c in colors]))
    set_buffer_attributes(l, t, reverted_colors)
    time.sleep(0.15)
    set_buffer_attributes(l, t, colors)

def set_console_title(title):
    """Set the title of the current console"""
    pass

def move_cursor(x, y):
    """Move the cursor to the specified location"""
    location = COORD(x, y)
    ctypes.windll.kernel32.SetConsoleCursorPosition(stdout_handle, location)

def get_cursor():
    """Get the current cursor position"""
    buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, pointer(buffer_info))
    return (buffer_info.cursorPosition.X, buffer_info.cursorPosition.Y)

def count_chars(start, end):
    return (end[1] - start[1]) * get_buffer_size()[0] + (end[0] - start[0])

def erase_to(end):
    from pycmd_public import color
    to_erase = count_chars(get_cursor(), end)
    sys.stdout.write(color.Fore.DEFAULT + color.Back.DEFAULT + ' ' * to_erase)
    cursor_backward(to_erase)

def get_buffer_size():
    """Get the size of the text buffer"""
    buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, pointer(buffer_info))
    return (buffer_info.size.X, buffer_info.size.Y)

def get_viewport():
    """Get the current viewport position"""
    buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, pointer(buffer_info))
    return (buffer_info.window.Left, buffer_info.window.Top, buffer_info.window.Right, buffer_info.window.Bottom)

def set_cursor_attributes(size, visibility):
    """Set the cursor size and visibility"""
    pass

def cursor_backward(count):
    """Move cursor backward with the given number of positions"""
    for i in range(count):
        sys.__stdout__.write('\b')
        sys.__stdout__.flush()

def scroll_buffer(lines):
    """Scroll vertically with the given (positive or negative) number of lines"""
    global scroll_mark
    (l, t, r, b) = get_viewport()
    (w, h) = get_buffer_size()
    if t + lines < 0:
        lines = -t              # Scroll up to beginning
    elif b + lines > h:
        lines = h - b - 1       # Scroll down to end
        
    if (lines < 0 and t >= lines or lines > 0 and b + lines <= h):
        info = SMALL_RECT(l, t + lines, r, b + lines)
        ctypes.windll.kernel32.SetConsoleWindowInfo(stdout_handle, True, byref(info))

def scroll_to_quarter(line):
    """Scroll up so that the specified line is at least 25% of the screen deep"""
    lines = line - get_viewport()[1]
    viewport_height = get_viewport()[3] - get_viewport()[1]
    if lines < viewport_height / 4:
        scroll_buffer(lines - viewport_height / 4)

def read_input():
    """Read one input event from stdin and translate it to a structure similar to KEY_EVENT_RECORD"""
    while len(input_buffer) == 0:
        time.sleep(0.1)
    ch = input_buffer.pop()
    #print('\n\rC1=0x%02X' % ch)
    match ch:
        case c if c == 0x04:  # Ctrl-D
            return PyINPUT_RECORDType(True, 0, chr(c), LEFT_CTRL_PRESSED)
        case c if c == 0x7F:  # Backspace
            return PyINPUT_RECORDType(True, 0, chr(8), 0)
        case c if c == 0x0A:  # Enter
            return PyINPUT_RECORDType(True, 0, '\x0D', 0)
        case c if c == 0x1B:  # Escape
            pty_control.input_processed = True
            while len(input_buffer) == 0:
                time.sleep(0.1)
            ch = input_buffer.pop()
            #print('\n\rC2=0x%02X' % ch)
            if ch == 0x5B:
                pty_control.input_processed = True
                while len(input_buffer) == 0:
                    time.sleep(0.1)
                ch = input_buffer.pop()
                #print('\n\rC3=0x%02X' % ch)
                if ch == 0x44:    # Left arrow
                    return PyINPUT_RECORDType(True, 37, chr(0), 0)
                elif ch == 0x43:  # Right arrow
                    return PyINPUT_RECORDType(True, 39, chr(0), 0)
                elif ch == 0x41:  # Up arrow
                    return PyINPUT_RECORDType(True, 38, chr(0), 0)
                elif ch == 0x42:  # Down arrow
                    return PyINPUT_RECORDType(True, 40, chr(0), 0)
                elif ch == 0x48:
                    return PyINPUT_RECORDType(True, 36, chr(0), 0)
                elif ch == 0x46:
                    return PyINPUT_RECORDType(True, 35, chr(0), 0)


    return PyINPUT_RECORDType(True, 0, chr(ch), 0)

def write_input(key_code, char, control_state):
    """Emulate a key press with the given key code and control key mask"""
    record = PyINPUT_RECORDType(KEY_EVENT)
    record.KeyDown = True
    record.VirtualKeyCode = key_code
    record.Char = char
    record.ControlKeyState = control_state
    stdin_handle.WriteConsoleInput([record])

def write_str(s):
    """
    Output s to stdout, while processing the color sequences
    """
    sys.__stdout__.write(remove_escape_sequences(s))
    sys.__stdout__.flush()


def get_current_foreground():
    return ''

def get_current_background():
    return ''

def remove_escape_sequences(s):
    """
    Remove color escape sequences from the given string
    
    """
    from pycmd_public import color
    escape_sequences_fore = [v for (k, v) in chain(color.Fore.__dict__.items(),
                                                   color.Back.__dict__.items())
                             if not k in ['__dict__', '__doc__', '__weakref__', '__module__']]
    return reduce(lambda x, y: x.replace(y, ''), 
                  escape_sequences_fore,
                  s)

def is_ctrl_pressed(record):
    """Check whether the Ctrl key is pressed"""
    return record.ControlKeyState & (LEFT_CTRL_PRESSED | RIGHT_CTRL_PRESSED) != 0

def is_alt_pressed(record):
    """Check whether the Alt key is pressed"""
    return record.ControlKeyState & (LEFT_ALT_PRESSED | RIGHT_ALT_PRESSED) != 0

def is_shift_pressed(record):
    """Check whether the Shift key is pressed"""
    return record.ControlKeyState & SHIFT_PRESSED != 0

def is_control_only(record):
    """
    Check whether this is a control-key-only press, i.e. just a modifier
    key w/out an "actual" key
    """
    return record.VirtualKeyCode in [16, 17, 18]

# Initialization
FOREGROUND_BLUE = 0x01
FOREGROUND_GREEN = 0x02
FOREGROUND_RED = 0x04
FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
FOREGROUND_BRIGHT = 0x08
BACKGROUND_BLUE = 0x10
BACKGROUND_GREEN = 0x20
BACKGROUND_RED = 0x40
BACKGROUND_BRIGHT = 0x80
BACKGROUND_WHITE = BACKGROUND_BLUE | BACKGROUND_GREEN | BACKGROUND_RED

class ColorOutputStream:
    """
    We install a custom sys.stdout that handles our color sequences

    Note that this requires sys.stdout be only imported _after_ console;
    not doing so will bring the original stdout in the current scope!
    """
    def write(self, str):
        """Dispatch printing to our enhanced write function"""
        write_str(str)

    def __getattr__(self, name):
        return getattr(sys.__stdout__, name)

# Install our custom output stream
sys.stdout = ColorOutputStream()

# Direct character processing
import tty
tty.setcbreak(sys.stdin)

# Buffer that is filled in by the pty callbacks
input_buffer = []
