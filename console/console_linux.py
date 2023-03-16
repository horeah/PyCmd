#
# Functions for manipulating the console using ANSI terminal sequences
#
import os
from pty import STDIN_FILENO
from itertools import chain
from functools import reduce
from dataclasses import dataclass
import ctypes, sys, locale, time
from ctypes import Structure, Union, c_int, c_long, c_char, c_wchar, c_short, pointer, byref
from ctypes.wintypes import BOOL, WORD, DWORD
import pty_control
from .console_common import *

# These are taken from the win32console
LEFT_ALT_PRESSED = 0x0002
LEFT_CTRL_PRESSED = 0x0008
RIGHT_ALT_PRESSED = 0x0001
RIGHT_CTRL_PRESSED = 0x0004
SHIFT_PRESSED = 0x0010

# Current formatting attributes (in windows format)
current_attributes = FOREGROUND_WHITE | BACKGROUND_BLACK

# Current cursor position
# 
# We perform our own cursor tracking in write_with_sane_cursor()
# because getting the actual cursor position using ANSI ESC[6n can
# easily interfere with actual keyboard input.
#
# Note that our tracked position is not the "absolute" cursor
# position, but rather a "relative" position compared to our own
# previous output (i.e. output that goes through our ColorOutputStream
# stdout replacement (and consequently through
# write_with_sane_cursor()
current_cursor = [0, 0]

# Write-back buffer used to emulate "write_input" (these will be
# consumed by read_input() before attempting to consume from the
# input_buffer)
write_back = []

@dataclass
class PyINPUT_RECORDType:
    KeyDown: bool = False
    VirtualKeyCode: int = 0
    Char: str = '\0'
    ControlKeyState: int = 0

KEYMAP_IDENT = {ch: PyINPUT_RECORDType(True, 0, chr(ch)) for ch in range(128)}
KEYMAP_NAVI = {
    0x44: PyINPUT_RECORDType(True, 37, chr(0), 0),  # Left arrow
    0x43: PyINPUT_RECORDType(True, 39, chr(0), 0),  # Right arrow
    0x41: PyINPUT_RECORDType(True, 38, chr(0), 0),  # Up arrow
    0x42: PyINPUT_RECORDType(True, 40, chr(0), 0),  # Down arrow
    0x48: PyINPUT_RECORDType(True, 36, chr(0), 0),  # Home
    0x46: PyINPUT_RECORDType(True, 35, chr(0), 0),  # End
}

KEYMAP = {
    **KEYMAP_IDENT,
    0x04: PyINPUT_RECORDType(True, 0, chr(0x04), LEFT_CTRL_PRESSED),  # Ctrl-D
    0x7F: PyINPUT_RECORDType(True, 0, chr(8), 0),  # Backspace
    0x0A: PyINPUT_RECORDType(True, 0, '\x0D', 0),  # Enter
    0x0B: PyINPUT_RECORDType(True, 75, 0, LEFT_CTRL_PRESSED),  # Ctrl-K
    0x01: PyINPUT_RECORDType(True, 65, 0, LEFT_CTRL_PRESSED),  # Ctrl-A
    0x03: PyINPUT_RECORDType(True, 67, 0, LEFT_CTRL_PRESSED),  # Ctrl-C
    0x05: PyINPUT_RECORDType(True, 69, 0, LEFT_CTRL_PRESSED),  # Ctrl-E
    0x07: PyINPUT_RECORDType(True, 71, 0, LEFT_CTRL_PRESSED),  # Ctrl-G
    0x10: PyINPUT_RECORDType(True, 80, 0, LEFT_CTRL_PRESSED),  # Ctrl-P
    0x0E: PyINPUT_RECORDType(True, 78, 0, LEFT_CTRL_PRESSED),  # Ctrl-N
    0x12: PyINPUT_RECORDType(True, 82, 0, LEFT_CTRL_PRESSED),  # Ctrl-R
    0x06: PyINPUT_RECORDType(True, 70, 0, LEFT_CTRL_PRESSED),  # Ctrl-F
    0x02: PyINPUT_RECORDType(True, 66, 0, LEFT_CTRL_PRESSED),  # Ctrl-B
    0x16: PyINPUT_RECORDType(True, 86, 0, LEFT_CTRL_PRESSED),  # Ctrl-V
    0x17: PyINPUT_RECORDType(True, 87, 0, LEFT_CTRL_PRESSED),  # Ctrl-W
    0x18: PyINPUT_RECORDType(True, 88, 0, LEFT_CTRL_PRESSED),  # Ctrl-X
    0x19: PyINPUT_RECORDType(True, 89, 0, LEFT_CTRL_PRESSED),  # Ctrl-Y
    0x1B: {  # Escape
        **KEYMAP_IDENT,
        0x7F: PyINPUT_RECORDType(True, 8, chr(8), LEFT_ALT_PRESSED), # Alt-Backspace
        0x1B: PyINPUT_RECORDType(True, 0, chr(27), 0),  # Escape
        0x2F: PyINPUT_RECORDType(True, 191, 0, LEFT_ALT_PRESSED),  # Alt-/
        0x62: PyINPUT_RECORDType(True, 66, 0, LEFT_ALT_PRESSED),   # Alt-B
        0x64: PyINPUT_RECORDType(True, 68, 0, LEFT_ALT_PRESSED),   # Alt-D
        0x66: PyINPUT_RECORDType(True, 70, 0, LEFT_ALT_PRESSED),   # Alt-F
        0x6E: PyINPUT_RECORDType(True, 78, 0, LEFT_ALT_PRESSED),   # Alt-N
        0x70: PyINPUT_RECORDType(True, 80, 0, LEFT_ALT_PRESSED),   # Alt-P
        0x5B: {  # [
            **KEYMAP_IDENT,
            **KEYMAP_NAVI,
            0x31: {  # ]
                **KEYMAP_IDENT,
                0x3B: {
                    **KEYMAP_IDENT,
                    0x33: {
                        **KEYMAP_IDENT,
                        **{k: PyINPUT_RECORDType(v.KeyDown, v.VirtualKeyCode, v.Char, LEFT_ALT_PRESSED)
                           for k, v in KEYMAP_NAVI.items()},
                    },
                    0x35: {
                        **KEYMAP_IDENT,
                        **{k: PyINPUT_RECORDType(v.KeyDown, v.VirtualKeyCode, v.Char, LEFT_ALT_PRESSED)
                           for k, v in KEYMAP_NAVI.items()},

                    },
                    0x32: {
                        **KEYMAP_IDENT,
                        **{k: PyINPUT_RECORDType(v.KeyDown, v.VirtualKeyCode, v.Char, SHIFT_PRESSED)
                           for k, v in KEYMAP_NAVI.items()},
                    },
                },
            },
            0x32: {
                **KEYMAP_IDENT,
                0x7E: PyINPUT_RECORDType(True, 45, chr(0), 0),  # Insert
            },
            0x33: {
                **KEYMAP_IDENT,
                0x7E: PyINPUT_RECORDType(True, 46, chr(0), 0),  # Delete
                0x3B: {
                    **KEYMAP_IDENT,
                    0x33: {
                        **KEYMAP_IDENT,
                        0x7E: PyINPUT_RECORDType(True, 46, chr(0), LEFT_ALT_PRESSED),  # Alt-Delete
                    },
                    0x35: {
                        **KEYMAP_IDENT,
                        0x7E: PyINPUT_RECORDType(True, 46, chr(0), LEFT_CTRL_PRESSED),  # Ctrl-Delete
                    },
                    0x32: {
                        **KEYMAP_IDENT,
                        0x7E: PyINPUT_RECORDType(True, 46, chr(0), SHIFT_PRESSED),  # Shift-Delete
                    },
                },
            },
            0x35: {
                **KEYMAP_IDENT,
                0x7E: PyINPUT_RECORDType(True, 33, chr(0), 0),  # PgUp
            },
            0x36: {
                **KEYMAP_IDENT,
                0x7E: PyINPUT_RECORDType(True, 34, chr(0), 0),  # PgDn
            },
        },
    },
}

def get_text_attributes():
    return current_attributes

def set_text_attributes(color):
    """Set foreground/background RGB components for the text to write"""
    R, G, B = (color & FOREGROUND_RED != 0,
               color & FOREGROUND_GREEN != 0,
               color & FOREGROUND_BLUE != 0)
    # sys.__stdout__.write('\r\nCOLOR:%02X RGB: %d %d %d\r\n' % (color, R, G, B))
    match R, G, B:
        case 0, 0, 0: seq = 30
        case 0, 0, 1: seq = 34
        case 0, 1, 0: seq = 32
        case 0, 1, 1: seq = 36
        case 1, 0, 0: seq = 31
        case 1, 0, 1: seq = 35
        case 1, 1, 0: seq = 33
        case 1, 1, 1: seq = 37
    #sys.__stdout__.write('\r\nSEQ: %d\r\n' % seq)
    if color & FOREGROUND_BRIGHT:
        seq += 60
    if seq == 37:
        seq = 39  # use "default" instead of white
    sys.__stdout__.write('\033[%dm' % seq)

    R, G, B = (color & BACKGROUND_RED != 0,
               color & BACKGROUND_GREEN != 0,
               color & BACKGROUND_BLUE != 0)
    # sys.__stdout__.write('\r\nCOLOR:%02X RGB: %d %d %d\r\n' % (color, R, G, B))
    match R, G, B:
        case 0, 0, 0: seq = 40
        case 0, 0, 1: seq = 44
        case 0, 1, 0: seq = 42
        case 0, 1, 1: seq = 46
        case 1, 0, 0: seq = 41
        case 1, 0, 1: seq = 45
        case 1, 1, 0: seq = 43
        case 1, 1, 1: seq = 47
    #sys.__stdout__.write('\r\nSEQ: %d\r\n' % seq)
    if color & BACKGROUND_BRIGHT:
        seq += 60
    if seq == 40:
        seq = 49  # use "default" instead of black
    sys.__stdout__.write('\033[%dm' % seq)

    sys.__stdout__.flush()
    global current_attributes
    current_attributes = color

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
    return

def set_console_title(title):
    """Set the title of the current console"""
    pass

def move_cursor(x, y):
    """Move the cursor to the specified location"""
    if x > current_cursor[0]:
        sys.__stdout__.write('\033[%dC' % (x - current_cursor[0]))
    elif x < current_cursor[0]:
        sys.__stdout__.write('\033[%dD' % (current_cursor[0] - x))
    if y > current_cursor[1]:
        sys.__stdout__.write('\033[%dB' % (y - current_cursor[1]))
    elif y < current_cursor[1]:
        sys.__stdout__.write('\033[%dA' % (current_cursor[1] - y))
    sys.__stdout__.flush()
    current_cursor[0] = x
    current_cursor[1] = y

def get_cursor():
    """Get the current cursor position"""
    return tuple(current_cursor)

def count_chars(start, end):
    return (end[1] - start[1]) * get_buffer_size()[0] + (end[0] - start[0])

def get_buffer_size():
    """Get the size of the text buffer"""
    return os.get_terminal_size()

def get_viewport():
    """Get the current viewport position"""
    return (0, 0, *get_buffer_size())

def set_cursor_attributes(size, visibility):
    """Set the cursor visibility (setting the size is not possible on Linux)"""
    sys.__stdout__.write('\033[?25%s' % ('h' if visibility else 'l'))
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
    if write_back:
        return write_back.pop(0)

    keymap = KEYMAP
    pty_control.input_processed.clear()
    ch = 0
    while True:
        if ch == 0x1B:
            # Try to guess if the ESC character is the ESC key being
            # pressed, or the beginning of a special sequence
            if not pty_control.input_available.wait(0.1):
                return mapped[ch]
        debug('read_input input_available.wait')
        pty_control.input_available.wait()
        debug('read_input got')
        pty_control.input_available.clear()
        ch = pty_control.input_buffer.pop()
        #debug('CH=0x%02X' % ch)
        mapped = keymap[ch]
        if isinstance(mapped, PyINPUT_RECORDType):
            return mapped
        else:
            # we are still in a sequence
            keymap = mapped
            debug('read_input input_processed.set')
            pty_control.input_processed.set()

def write_input(key_code, char, control_state):
    """Emulate a key press with the given key code and control key mask"""
    write_back.append(PyINPUT_RECORDType(True, key_code, char, control_state))

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

def write_with_sane_cursor(s):
    """Write simple text (i.e. no escape sequences) and track the
    (relative) cursor position; also ensure that the cursor is
    automatically moved to the next line when the end of a line is
    reached (this does not happen by default!)
    """
    buffer_size = get_buffer_size()
    for c in s:
        sys.__stdout__.write(c)
        if c == '\r':
            current_cursor[0] = 0
        elif c == '\b':
            current_cursor[0] -= 1
            if current_cursor[0] < 0:
                current_cursor[0] = 0
        elif c == '\n':
            current_cursor[1] += 1
            write_with_sane_cursor('\r')
        else:
            current_cursor[0] += 1
            if current_cursor[0] >= buffer_size[0]:
                sys.__stdout__.write('\r\n')
                current_cursor[1] += 1
                current_cursor[0] = 0
        if current_cursor[1] >= buffer_size[1]:
            current_cursor[1] = buffer_size[1] - 1

