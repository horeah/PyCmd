#
# Functions for manipulating the console using Microsoft's Console API
#
import ctypes
from ctypes import Structure, Union, c_int, c_long, c_char, c_wchar, c_short, pointer, byref
from ctypes.wintypes import BOOL, WORD, DWORD

global FOREGROUND_RED
global FOREGROUND_GREEN
global FOREGROUND_BLUE
global FOREGROUND_WHITE
global FOREGROUND_BRIGHT

global BACKGROUND_RED
global BACKGROUND_GREEN
global BACKGROUND_BLUE
global BACKGROUND_BRIGHT

global stdout_handle
global stdin_handle

class COORD(Structure):
    _fields_ = [('X', c_short),
                ('Y', c_short)]

class SMALL_RECT(Structure):
    _fields_ = [('Left', c_short),
                ('Top', c_short),
                ('Right', c_short),
                ('Bottom', c_short)]

class CONSOLE_CURSOR_INFO(Structure):
    _fields_ = [('size', c_int),
                ('visible', c_int)]

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [('size', COORD),
                ('cursorPosition', COORD),
                ('attributes', WORD),
                ('window', SMALL_RECT),
                ('maxWindowSize', COORD)]

class KEY_EVENT_RECORD(Structure):
    _fields_ = [('keyDown', BOOL),
                ('repeatCount', WORD),
                ('virtualKeyCode', WORD),
                ('virtualScanCode', WORD),
                ('char', c_char),
                ('controlKeyState', DWORD)]
    
class INPUT_RECORD(Structure):
    _fields_ = [('EventType', WORD),
                ('Event', KEY_EVENT_RECORD)]


def get_text_attributes():
    """Get the current foreground/background RGB components"""
    buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, pointer(buffer_info))
    return buffer_info.attributes

def set_text_attributes(color):
    """Set foreground/background RGB components for the text to write"""
    ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, color)

def set_console_title(title):
    """Set the title of the current console"""
    ctypes.windll.kernel32.SetConsoleTitleA(title)

def move_cursor(x, y):
    """Move the cursor to the specified location"""
    location = COORD(x, y)
    ctypes.windll.kernel32.SetConsoleCursorPosition(stdout_handle, location)

def get_cursor():
    """Get the current cursor position"""
    buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, pointer(buffer_info))
    return (buffer_info.cursorPosition.X, buffer_info.cursorPosition.Y)

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

def set_cursor_visible(vis):
    """Set the visibility of the cursor"""
    cursor_info = CONSOLE_CURSOR_INFO(10, vis)
    ctypes.windll.kernel32.SetConsoleCursorInfo(stdout_handle, pointer(cursor_info))

def cursor_backward(count):
    """Move cursor backward with the given number of positions"""
    (x, y) = get_cursor()
    while count > 0:
        x -= 1
        if x < 0:
            y -= 1
            (x, _) = get_buffer_size()
            x -= 1
        count -= 1
    move_cursor(x, y)

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

def read_input():
    """Read one input event from the console input buffer"""
    record = INPUT_RECORD()
    records_read = c_long(0)
    while True:
        ctypes.windll.kernel32.ReadConsoleInputA(stdin_handle, byref(record), 1, byref(records_read))
        # print '\n\n', record.EventType, '\n\n'
        if record.EventType == 0x001 and record.Event.keyDown == True:
            return record.Event

def write_input(key_code, control_state):
    """Emulate a key press with the given key code and control key mask"""
    record = INPUT_RECORD()
    record.EventType = 0x001
    record.Event.keyDown = True
    record.Event.virtualKeyCode = key_code
    record.Event.controlKeyState = control_state
    records_read = c_long(0)
    ctypes.windll.kernel32.WriteConsoleInputA(stdin_handle, byref(record), 1, byref(records_read))

def is_ctrl_pressed(record):
    """Check whether the Ctrl key is pressed"""
    return record.controlKeyState & (0x0008 | 0x0004) != 0

def is_alt_pressed(record):
    """Check whether the Alt key is pressed"""
    return record.controlKeyState & (0x0001 | 0x0002) != 0

def is_shift_pressed(record):
    """Check whether the Shift key is pressed"""
    return record.controlKeyState & 0x0010 != 0

def is_control_only(record):
    """
    Check whether this is a control-key-only press, i.e. just a modifier
    key w/out an "actual" key
    """
    return record.virtualKeyCode in [16, 17, 18]

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

stdin_handle = ctypes.windll.kernel32.GetStdHandle(-10)
stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
