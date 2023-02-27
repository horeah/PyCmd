import sys
from . import console_common

if sys.platform == 'win32':
    from .console_win32 import *
else:
    from .console_linux import *

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

def erase_to(end):
    from pycmd_public import color
    to_erase = count_chars(get_cursor(), end)
    sys.stdout.write(color.Fore.DEFAULT + color.Back.DEFAULT + ' ' * to_erase)
    cursor_backward(to_erase)

def write_str(s):
    """
    Output s to stdout, while processing the color sequences
    """
    i = 0
    buf = ''
    attr = get_text_attributes()
    while i < len(s):
        c = s[i]
        if c == chr(27):
            if buf:
                # We have some characters, apply attributes and write them out
                set_text_attributes(attr)
                write_with_sane_cursor(buf)
                buf = ''

            # Process color commands to compute and set new attributes
            target = s[i + 1]
            command = s[i + 2]
            component = s[i + 3]
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
            bit_mask = console_common.__dict__[name_prefix + '_' + name_suffix]
            attr = operator(attr, bit_mask)
        else:
            # Regular character, just append to the buffer
            buf += c
        i += 1

    # Apply the last attributes and write the remaining chars (if any)
    set_text_attributes(attr)
    if buf:
        write_with_sane_cursor(buf)

    
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
