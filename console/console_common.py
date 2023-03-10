#
# Common console constants, datatypes and definitions (used on both
# Windows and Linux)
#
import threading
from ctypes import Structure, Union, c_int, c_long, c_char, c_wchar, c_short
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

# Color bit constants (Windows style)
FOREGROUND_BLACK = 0x00
FOREGROUND_BLUE = 0x01
FOREGROUND_GREEN = 0x02
FOREGROUND_RED = 0x04
FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
FOREGROUND_BRIGHT = 0x08

BACKGROUND_BLACK = 0x00
BACKGROUND_BLUE = 0x10
BACKGROUND_GREEN = 0x20
BACKGROUND_RED = 0x40
BACKGROUND_BRIGHT = 0x80
BACKGROUND_WHITE = BACKGROUND_BLUE | BACKGROUND_GREEN | BACKGROUND_RED

debug_file = open('PyCmd_debug.txt', 'w')
debug_lock = threading.Lock()
def debug(message):
    with debug_lock:
        debug_file.write(str(message) + '\n')
        debug_file.flush()

