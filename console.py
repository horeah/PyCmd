#
# Functions for manipulating the console using Microsoft's Console API
#
import ctypes, sys, locale, time
from ctypes import Structure, Union, c_int, c_long, c_char, c_wchar, c_short, pointer, byref
from ctypes.wintypes import BOOL, WORD, DWORD
from win32console import GetStdHandle, STD_INPUT_HANDLE, PyINPUT_RECORDType, KEY_EVENT
from win32con import LEFT_CTRL_PRESSED, RIGHT_CTRL_PRESSED
from win32con import LEFT_ALT_PRESSED, RIGHT_ALT_PRESSED
from win32con import SHIFT_PRESSED

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
    cursor_info = CONSOLE_CURSOR_INFO(size, visibility)
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

def scroll_to_quarter(line):
    """Scroll up so that the specified line is at least 25% of the screen deep"""
    lines = line - get_viewport()[1]
    viewport_height = get_viewport()[3] - get_viewport()[1]
    if lines < viewport_height / 4:
        scroll_buffer(lines - viewport_height / 4)

def read_input():
    """Read one input event from the console input buffer"""
    while True:
        record = stdin_handle.ReadConsoleInput(1)[0]
        if record.EventType == KEY_EVENT and record.KeyDown:
            return record

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
    Output s to stdout (after encoding it with stdout encoding to
    avoid conversion errors with non ASCII characters)
    """
    def write_with_sane_cursor(s):
        """
        Under Win10, write() no longer advances the cursor to the next line after writing in the last column; so we
        use a custom function to restore that behavior when needed
        """
        buffer_width = get_buffer_size()[0]
        cursor_before = get_cursor()[0]
        sys.__stdout__.write(s)
        cursor_after = get_cursor()[0]
        if (buffer_width > 0
            and (cursor_before + len(s)) % buffer_width == 0
            and cursor_after > 0):
            # We have written over until the last column, but the cursor is NOT pushed to the next line; so we push it
            # ourselves
            sys.__stdout__.write(' \r')

    if sys.__stdout__.encoding:
        encoded_str = s.encode(sys.__stdout__.encoding, 'replace')
    else:
        encoded_str = s
    i = 0
    buf = ''
    attr = get_text_attributes()
    while i < len(encoded_str):
        c = encoded_str[i]
        if c == chr(27):
            if buf:
                # We have some characters, apply attributes and write them out
                set_text_attributes(attr)
                write_with_sane_cursor(buf)
                buf = ''

            # Process color commands to compute and set new attributes
            target = encoded_str[i + 1]
            command = encoded_str[i + 2]
            component = encoded_str[i + 3]
            i += 3

            # Escape sequence format is [ESC][TGT][OP][COMP], where:
            #  * ESC is the Escape character: chr(27)
            #  * TGT is the target: 'F' for foreground, 'B' for background
            #  * OP is the operation: 'S' (set), 'C' (clear), 'T' (toggle) a component
            #  * COMP is the color component: 'R', 'G', 'B' or 'X' (bright)
            if target == 'F':
                name_prefix = 'FOREGROUND'
            else:
                name_prefix = 'BACKGROUND'

            if component == 'R':
                name_suffix = 'RED'
            elif component == 'G':
                name_suffix = 'GREEN'
            elif component == 'B':
                name_suffix = 'BLUE'
            else:
                name_suffix = 'BRIGHT'

            if command == 'S':
                operator = lambda x, y: x | y
            elif command == 'C':
                operator = lambda x, y: x & ~y
            else:
                operator = lambda x, y: x ^ y

            import console
            # We use the bit masks defined at the end of console.py by computing
            # the name and accessing the module's dictionary (FOREGROUND_RED,
            # BACKGROUND_BRIGHT etc)
            bit_mask = console.__dict__[name_prefix + '_' + name_suffix]
            attr = operator(attr, bit_mask)
        else:
            # Regular character, just append to the buffer
            buf += c
        i += 1

    # Apply the last attributes and write the remaining chars (if any)
    set_text_attributes(attr)
    if buf:
        write_with_sane_cursor(buf)

def remove_escape_sequences(s):
    """
    Remove color escape sequences from the given string
    
    """
    from pycmd_public import color
    escape_sequences_fore = [v for (k, v) in color.Fore.__dict__.items() + color.Back.__dict__.items()
                             if not k in ['__dict__', '__doc__', '__weakref__', '__module__']]
    return reduce(lambda x, y: x.replace(y, ''), 
                  escape_sequences_fore,
                  s)

def get_current_foreground():
    """Get the current foreground setting as a color string"""
    color = ''
    attr = get_text_attributes()
    letters = ['B', 'G', 'R', 'X']

    for i in range(4):
        if attr & 1 << i:
            color += chr(27) + 'FS' + letters[i]
        else:
            color += chr(27) + 'FC' + letters[i]

    return color

def get_current_background():
    """Get the current background setting as a color string"""
    color = ''
    attr = get_text_attributes()
    letters = ['B', 'G', 'R', 'X']

    for i in range(4):
        if attr & 1 << (i + 4):
            color += chr(27) + 'BS' + letters[i]
        else:
            color += chr(27) + 'BC' + letters[i]

    return color

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

stdin_handle = GetStdHandle(STD_INPUT_HANDLE)
stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)

class ColorOutputStream:
    """
    We install a custom sys.stdout that handles:
     * our color sequences
     * string encoding

     Note that this requires sys.stdout be only imported _after_ console;
     not doing so will bring the original stdout in the current scope!
     """
    encoding = sys.__stdout__.encoding
    
    def write(self, str):
        """Dispatch printing to our enhanced write function"""
        write_str(str)

# Set default encoding to the system's locale; this needs to be done here,
# before we install the custom output stream (since we reload(sys))
reload(sys)
sys.setdefaultencoding(locale.getdefaultlocale()[1])

# Install our custom output stream
sys.stdout = ColorOutputStream()
