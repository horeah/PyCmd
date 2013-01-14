"""
Public constants, objects and utilities exported by PyCmd.

These are meant to be used in init.py files; users can rely on them being kept
unchanged (interface-wise) throughout later versions.
"""
import os, sys, common, console

def abbrev_path(path = None):
    """
    Abbreviate a full path (or the current path, if None is provided) to make
    it shorter, yet still unambiguous.

    This function takes a directory path and tries to abbreviate it as much as
    possible while making sure that the resulting shortened path is not
    ambiguous: a path element is only abbreviated if its shortened form is
    unique in its directory (in other words, if a sybling would have the same
    abbreviation, the original name is kept).

    The abbreviation is performed by keeping only the first letter of each
    "word" composing a path element. "Words" are defined by CamelCase,
    underscore_separation or "whitespace separation".
    """
    if not path:
        path = os.getcwd().decode(sys.getfilesystemencoding())
        path = path[0].upper() + path[1:]
    current_dir = path[ : 3]
    path = path[3 : ]
    path_abbrev = current_dir[ : 2]

    for elem in path.split('\\')[ : -1]:
        elem_abbrev = common.abbrev_string(elem)
        for other in os.listdir(current_dir):
            if os.path.isdir(current_dir + '\\' + other) and common.abbrev_string(other).lower() == elem_abbrev.lower() and other.lower() != elem.lower():
                # Found other directory with the same abbreviation
                # In this case, we use the entire name
                elem_abbrev = elem
                break
        current_dir += '\\' + elem
        path_abbrev += '\\' + elem_abbrev

    return path_abbrev + '\\' + path.split('\\')[-1]


def abbrev_path_prompt():
    """
    Return a prompt containg the current path (abbreviated)

    This is the default PyCmd prompt. It uses the abbrev_path() function to
    obtain the shortened path and appends the typical '> '.
    """
    return abbrev_path() + u'> '


class color(object):
    """
    Constants for color manipulation within PyCmd.

    These constants are similar to ANSI escape sequences, only more powerful in
    the sense that they support setting, resetting and toggling of individual R,
    G, B components
    """

    class Fore(object):
        """Color constants for the foreground"""

        # For individually setting a RGB field
        SET_RED = chr(27) + 'FSR'
        SET_GREEN = chr(27) + 'FSG'
        SET_BLUE = chr(27) + 'FSB'
        SET_BRIGHT = chr(27) +'FSX'

        # For individually clearing a RGB field
        CLEAR_RED = chr(27) + 'FCR'
        CLEAR_GREEN = chr(27) + 'FCG'
        CLEAR_BLUE = chr(27) + 'FCB'
        CLEAR_BRIGHT = chr(27) + 'FCX'

        # For individually toggling a RGB field
        TOGGLE_RED = chr(27) + 'FTR'
        TOGGLE_GREEN = chr(27) + 'FTG'
        TOGGLE_BLUE = chr(27) + 'FTB'
        TOGGLE_BRIGHT = chr(27) + 'FTX'


        # Standard colors defined as combinations of the RGB constants
        RED = SET_RED + CLEAR_GREEN + CLEAR_BLUE
        GREEN = CLEAR_RED + SET_GREEN + CLEAR_BLUE
        YELLOW = SET_RED + SET_GREEN + CLEAR_BLUE
        BLUE = CLEAR_RED + CLEAR_GREEN + SET_BLUE
        MAGENTA = SET_RED + CLEAR_GREEN + SET_BLUE
        CYAN = CLEAR_RED + SET_GREEN + SET_BLUE
        WHITE = SET_RED + SET_GREEN + SET_BLUE

        # Default terminal color
        DEFAULT = console.get_current_foreground()


    class Back(object):
        """Color constants for the background"""

        # For individually setting a RGB field
        SET_RED = chr(27) + 'BSR'
        SET_GREEN = chr(27) + 'BSG'
        SET_BLUE = chr(27) + 'BSB'
        SET_BRIGHT = chr(27) +'BSX'

        # For individually clearing a RGB field
        CLEAR_RED = chr(27) + 'BCR'
        CLEAR_GREEN = chr(27) + 'BCG'
        CLEAR_BLUE = chr(27) + 'BCB'
        CLEAR_BRIGHT = chr(27) + 'BCX'

        # For individually toggling a RGB field
        TOGGLE_RED = chr(27) + 'BTR'
        TOGGLE_GREEN = chr(27) + 'BTG'
        TOGGLE_BLUE = chr(27) + 'BTB'
        TOGGLE_BRIGHT = chr(27) + 'BTX'

        # Standard colors defined as combinations of the RGB constants
        RED = SET_RED + CLEAR_GREEN + CLEAR_BLUE
        GREEN = CLEAR_RED + SET_GREEN + CLEAR_BLUE
        YELLOW = SET_RED + SET_GREEN + CLEAR_BLUE
        BLUE = CLEAR_RED + CLEAR_GREEN + SET_BLUE
        MAGENTA = SET_RED + CLEAR_GREEN + SET_BLUE
        CYAN = CLEAR_RED + SET_GREEN + SET_BLUE
        WHITE = SET_RED + SET_GREEN + SET_BLUE

        # Default terminal color
        DEFAULT = console.get_current_background()

    @staticmethod
    def update():
        """
        Update the current values of the DEFAULT color constant -- we have
        to adapt these since they might change (e.g. with the "color"
        command).
        """
        color.Back.DEFAULT = console.get_current_background()
        color.Fore.DEFAULT = console.get_current_foreground()

class _Settings(object):
    """
    Generic settings class; extend this to create a "group" of options
    (accessible as instance members in the settings.py files)
    """
    def sanitize(self):
        """Make sure the settings have sane values"""
        pass


class _Appearance(_Settings):
    """Appearance settings"""

    class _ColorSettings(_Settings):
        """Color-related settings"""
        def __init__(self):
            self.text = ''
            self.prompt = color.Fore.TOGGLE_BRIGHT
            self.selection = (color.Fore.TOGGLE_RED +
                              color.Fore.TOGGLE_GREEN +
                              color.Fore.TOGGLE_BLUE +
                              color.Back.TOGGLE_RED +
                              color.Back.TOGGLE_GREEN +
                              color.Back.TOGGLE_BLUE)
            self.search_filter = (color.Back.TOGGLE_RED +
                                  color.Back.TOGGLE_BLUE +
                                  color.Fore.TOGGLE_BRIGHT)
            self.completion_match = color.Fore.TOGGLE_RED
            self.dir_history_selection = (color.Fore.TOGGLE_BRIGHT +
                                          color.Back.TOGGLE_BRIGHT)

    def __init__(self):
        # Prompt function (should return a string)
        self.prompt = abbrev_path_prompt

        # Color configuration
        self.colors = self._ColorSettings()

    def sanitize(self):
        if not callable(self.prompt):
            print 'Prompt function doesn\'t look like a callable; reverting to PyCmd\'s default prompt'
            self.prompt = abbrev_path_prompt


class Behavior(_Settings):
    """Behavior settings"""
    def __init__(self):
        # Skip splash message (welcome and bye).
        # This can be also overriden with the '-Q' command line argument'
        self.quiet_mode = False

        # Select the completion mode; currently supported: 'bash'
        self.completion_mode = 'bash'

    def sanitize(self):
        if not self.completion_mode in ['bash']:
            print 'Invalid setting "' + self.completion_mode + '" for "completion_mode" -- using default "bash"'
            self.completion_mode = 'bash'


# Initialize global configuration instances with default values
#
# These objects are directly manipulated by the settings.py files, executed via
# apply_settings(). Then, they are directly used by PyCmd.py to get the current
# configuration settings
appearance = _Appearance()
behavior = Behavior()
