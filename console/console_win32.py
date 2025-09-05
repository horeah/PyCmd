#
# Functions for manipulating the console using Microsoft's Console API
#
from itertools import chain
from functools import reduce
import ctypes, sys, locale, time
from ctypes import Structure, Union, c_int, c_long, c_char, c_wchar, c_short, pointer, byref
from ctypes.wintypes import BOOL, WORD, DWORD
from win32console import GetStdHandle, STD_INPUT_HANDLE, PyINPUT_RECORDType, KEY_EVENT
from win32con import LEFT_CTRL_PRESSED, RIGHT_CTRL_PRESSED
from win32con import LEFT_ALT_PRESSED, RIGHT_ALT_PRESSED
from win32con import SHIFT_PRESSED
from .console_common import *

def get_text_attributes():
    """Get the current foreground/background RGB components"""
    buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, pointer(buffer_info))
    return buffer_info.attributes

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
    ctypes.windll.kernel32.SetConsoleTitleA(title.encode(sys.stdout.encoding))

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
    cursor_info = CONSOLE_CURSOR_INFO(size, visibility)
    ctypes.windll.kernel32.SetConsoleCursorInfo(stdout_handle, pointer(cursor_info))

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

def clear_screen():
    """Clear the screen and move the cursor to the top-left corner"""
    from pycmd_public import color
    width, height = get_buffer_size()
    sys.stdout.write(color.Fore.DEFAULT + color.Back.DEFAULT + ' ' * width * height)
    move_cursor(0, 0)

def read_input():
    """Read one input event from the console input buffer"""
    while True:
        record = stdin_handle.ReadConsoleInput(1)[0]
        if record.EventType == KEY_EVENT and record.KeyDown:
            # debug('%s %d' % (record.Char, record.VirtualKeyCode))
            return record

def write_input(key_code, char, control_state):
    """Emulate a key press with the given key code and control key mask"""
    record = PyINPUT_RECORDType(KEY_EVENT)
    record.KeyDown = True
    record.VirtualKeyCode = key_code
    record.Char = char
    record.ControlKeyState = control_state
    stdin_handle.WriteConsoleInput([record])

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
    """
    Under Win10, write() no longer advances the cursor to the next line after writing in the last column; so we
    use a custom function to restore that behavior when needed
    """
    buffer_width = get_buffer_size()[0]
    cursor_before = get_cursor()[0]
    sys.__stdout__.write(s)
    sys.__stdout__.flush()
    cursor_after = get_cursor()[0]
    if (buffer_width > 0
        and (cursor_before + len(s)) % buffer_width == 0
        and cursor_after > 0):
        # We have written over until the last column, but the cursor is NOT pushed to the next line; so we push it
        # ourselves
        sys.__stdout__.write(' \r')

stdin_handle = GetStdHandle(STD_INPUT_HANDLE)
stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)

