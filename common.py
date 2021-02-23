#
# Common utility functions
#
import os, string, fsm, _winreg, pefile, mmap, sys, traceback
from console import get_cursor, move_cursor, get_viewport
import re
import pycmd_public

_debug_messages = []
def debug(message):
    queue_len = 6
    width = 50
    _debug_messages.append(message)
    if len(_debug_messages) > queue_len:
        _debug_messages.pop(0)
    orig_cursor = get_cursor()
    v_left, v_top, _, _ = get_viewport()
    move_cursor(v_left, v_top)
    sys.stdout.write(pycmd_public.color.Back.TOGGLE_RED)
    for m in _debug_messages:
        sys.stdout.write('| %-*s |\n' % (width - 1, m))
    sys.stdout.write('+' + (width + 1) * '-' + '+')
    sys.stdout.write(pycmd_public.color.Back.TOGGLE_RED)
    move_cursor(orig_cursor[0], orig_cursor[1])


# Stop points when navigating one word at a time
word_sep = [' ', '\t', '\\', '-', '_', '.', '/', '$', '&', '=', '+', '@', ':', ';', '"']

# Command splitting characters
sep_chars = [' ', '|', '&', '>', '<']

# Command sequencing tokens
seq_tokens = ['|', '||', '&', '&&']

# Redirection tokens
digit_chars = list(string.digits)
redir_file_simple = ['>', '>>', '<']
redir_file_ext = [c + d for d in digit_chars for c in ['<&', '>&']]
redir_file_all = redir_file_simple + redir_file_ext
redir_file_tokens = redir_file_all + [d + c for d in digit_chars for c in redir_file_all]
# print redir_file_tokens

# All command splitting tokens
sep_tokens = seq_tokens + redir_file_tokens

# Executable extensions (all lowercase), as indicated by the PATHSPEC
exec_extensions = os.environ['PATHEXT'].lower().split(os.pathsep)

# Pseudo environment variables
pseudo_vars = ['CD', 'DATE', 'ERRORLEVEL', 'RANDOM', 'TIME']

def parse_line(line):
    """Tokenize a command line based on whitespace while observing quotes"""

    def accumulate(fsm):
        """Action: add current symbol to last token in list."""
        fsm.memory[-1] = fsm.memory[-1] + fsm.input_symbol

    def start_empty_token(fsm):
        """Action: start a new token."""
        if fsm.memory[-1] != '':
            fsm.memory.append('')

    def start_token(fsm):
        """Action: start a new token and accumulate."""
        start_empty_token(fsm)
        accumulate(fsm)

    def accumulate_last(fsm):
        """Action: accumulate and start new token."""
        accumulate(fsm)
        start_empty_token(fsm)

    def error(fsm):
        """Action: handle uncovered transition (should never happen)."""
        print 'Unhandled transition:', (fsm.input_symbol, fsm.current_state)
        accumulate(fsm)

    f = fsm.FSM('init', [''])

    f.set_default_transition(error, 'init')

    # default
    f.add_transition_list(string.whitespace, 'init', start_empty_token, 'whitespace')
    f.add_transition('"', 'init', accumulate, 'in_string')
    f.add_transition('|', 'init', start_token, 'pipe')
    f.add_transition('&', 'init', start_token, 'amp')
    f.add_transition('>', 'init', start_token, 'gt')
    f.add_transition('<', 'init', accumulate, 'awaiting_&')
    f.add_transition('^', 'init', accumulate, 'escape')
    f.add_transition_list(string.digits, 'init', accumulate, 'redir')
    f.add_transition_any('init', accumulate, 'init')

    # whitespace
    f.add_transition_list(string.whitespace, 'whitespace', None, 'whitespace')
    f.add_empty_transition('whitespace', 'init')

    # strings
    f.add_transition('"', 'in_string', accumulate, 'init')
    f.add_transition_any('in_string', accumulate, 'in_string')

    # seen '|'
    f.add_transition('|', 'pipe', accumulate_last, 'init')
    f.add_empty_transition('pipe', 'init', start_empty_token)

    # seen '&'
    f.add_transition('&', 'amp', accumulate_last, 'init')
    f.add_empty_transition('amp', 'init', start_empty_token)

    # seen '>' or '1>' etc.
    f.add_transition('>', 'gt', accumulate, 'awaiting_&')
    f.add_transition('&', 'gt', accumulate, 'awaiting_nr')
    f.add_empty_transition('gt', 'init', start_empty_token)

    # seen digit
    f.add_transition('<', 'redir', accumulate, 'awaiting_&')
    f.add_transition('>', 'redir', accumulate, 'gt')
    f.add_empty_transition('redir', 'init')

    # seen '<' or '>>', '0<', '2>>' etc.
    f.add_transition('&', 'awaiting_&', accumulate, 'awaiting_nr')
    f.add_empty_transition('awaiting_&', 'init', start_empty_token)

    # seen '<&' or '>&', '>>&', '0<&', '1>&', '2>>&' etc.
    f.add_transition_list(string.digits, 'awaiting_nr', accumulate_last, 'init')
    f.add_empty_transition('awaiting_nr', 'init', start_empty_token)

    # seen '^'
    f.add_transition_any('escape', accumulate, 'init')

    f.process_list(line)
    if len(f.memory) > 0 and f.memory[-1] == '':
        del f.memory[-1]

    return f.memory


def tokenize(line):
    """
    Wrapper for parse_line that appends an empty token if it detects a new token is beginning
    """
    tokens = parse_line(line)
    if tokens == [] or (line[-1] in sep_chars and parse_line(line) == parse_line(line + ' ')):
        tokens += ['']   # This saves us some checks later
    return tokens


def unescape(string):
    """Unescape string from ^ escaping. ^ inside double quotes is ignored"""
    if (string == None):
        return None
    result = u''
    in_quotes = False
    escape_next = False
    for c in string:
        if in_quotes:
            result += c
            if c == '"':
                in_quotes = False
        elif escape_next:
            result += c
            escape_next = False
        else:
            if c == '^':
                escape_next = True
            else:
                result += c
                if c == '"':
                    in_quotes = True

    return result


def expand_tilde(string):
    """
    Return an expanded version of the string by replacing a leading tilde
    with %HOME% (if defined) or %USERPROFILE%.
    """
    if 'HOME' in os.environ.keys():
        home_var = 'HOME'
    else:
        home_var = 'USERPROFILE'
    if string.startswith('~') or string.startswith('"~'):
        string = string.replace('~', '%' + home_var + '%', 1)
    return string


def expand_env_vars(string):
    """
    Return an expanded version of the string by inlining the values of the
    environment variables. Also replaces ~ with %HOME% or %USERPROFILE%.
    The provided string is expected to be a single token of a command.
    """
    # Expand tilde 
    string = expand_tilde(string)

    # Expand all %variable%s
    begin = string.find('%')
    while begin >= 0:
        end = string.find('%', begin + 1)
        if end >= 0:
            # Found a %variable%
            var = string[begin:end].strip('%')
            if var.upper() in os.environ.keys():
                string = string.replace('%' + var + '%', os.environ[var], 1)
        begin = string.find('%', begin + 1)

    return string


def split_nocase(string, separator):
    """Split a string based on the separator while ignoring case"""
    chunks = []
    seps = []
    pos = string.lower().find(separator.lower())
    while pos >= 0:
        chunks.append(string[ : pos])
        seps.append(string[pos : pos + len(separator)])
        string = string[pos + len(separator) : ]
        pos = string.lower().find(separator.lower())

    chunks.append(string)
    return (chunks, seps)


def fuzzy_match(substr, str, prefix_only = False):
    """
    Check if a substring is part of a string, while ignoring case and
    allowing for "fuzzy" matching, i.e. require that only the "words" in
    substr be individually matched in str (instead of an full match of
    substr). The prefix_only option only matches "words" in the substr at
    word boundaries in str.
    """
    #print '\n\nMatch "' + substr + '" in "' + str + '"\n\n'
    words = substr.split(' ')
    pattern = [('\\b' if prefix_only else '') + '(' + word + ').*' for word in words]
    # print '\n\n', pattern, '\n\n'
    pattern = ''.join(pattern)
    matches = re.search(pattern, str, re.IGNORECASE)
    return [matches.span(i) for i in range(1, len(words) + 1)] if matches else []

def abbrev_string(string):
    """Abbreviate a string by keeping uppercase and non-alphabetical characters"""
    string_abbrev = ''
    add_next_char = True

    for char in string:
        add_this_char = add_next_char
        if char == ' ':
            add_this_char = False
            add_next_char = True
        elif not char.isalpha():
            add_this_char = True
            add_next_char = True
        elif char.isupper() and not string.isupper():
            add_this_char = True
            add_next_char = False
        else:
            add_next_char = False
        if add_this_char:
            string_abbrev += char

    return string_abbrev

def has_exec_extension(file_name):
    """Check whether the specified file is executable, i.e. its extension is .exe, .com, .bat etc"""
    return os.path.splitext(file_name)[1].lower() in exec_extensions

def strip_extension(file_name):
    """Remove extension, if present"""
    dot = file_name.rfind('.')
    if dot > file_name.rfind('\\'):
        return file_name[ : dot]
    else:
        return file_name


def contains_special_char(string):
    """Check whether the string contains a character that requires quoting"""
    return string.find(' ') >= 0 or string.find('&') >= 0


def starts_with_special_char(string):
    """Check whether the string STARTS with a character that requires quoting"""
    return string.find(' ') == 0 or string.find('&') == 0


def associated_application(ext):
    """
    Scan the registry to find the application associated to a given file 
    extension.
    """
    try:
        file_class = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT, ext) or ext
        action = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT, file_class + '\\shell') or 'open'
        assoc_key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 
                                    file_class + '\\shell\\' + action + '\\command')
        open_command = _winreg.QueryValueEx(assoc_key, None)[0]
        
        # We assume a value `similar to '<command> %1 %2'
        return expand_env_vars(parse_line(open_command)[0])
    except WindowsError, e:
        return None


def full_executable_path(app_unicode):
    """
    Compute the full path of the executable that will be spawned 
    for the given command
    """
    app = app_unicode.encode(sys.getfilesystemencoding())

    # Split the app into a dir, a name and an extension; we
    # will configure our search for the actual executable based
    # on these
    dir, file = os.path.split(app.strip('"'))
    name, ext = os.path.splitext(file)

    # Determine possible executable extension
    if ext != '':
        extensions_to_search = [ext]
    else:
        extensions_to_search = exec_extensions

    # Determine the possible locations
    if dir:
        paths_to_search = [dir]
    else:
        paths_to_search = [os.getcwd()] + os.environ['PATH'].split(os.pathsep)

    # Search for an app
    # print 'D:', paths_to_search, 'N:', name, 'E:', extensions_to_search
    for p in paths_to_search:
        for e in extensions_to_search:
            full_path = os.path.join(p, name) + e
            if os.path.exists(full_path):
                return full_path

    # We could not find the executable; this might be an internal command,
    # or a file that doesn't have a registered application
    return None


def is_gui_application(executable):
    """
    Try to guess if an executable is a GUI or console app.
    Note that the full executable name of an .exe file is 
    required (use e.g. full_executable_path() to get it)
    """
    result = False
    try:
        fd = os.open(executable, os.O_RDONLY)
        m = mmap.mmap(fd, 0, access = mmap.ACCESS_READ)
        
        try:
            pe = pefile.PE(data = m, fast_load=True)
            if pefile.SUBSYSTEM_TYPE[pe.OPTIONAL_HEADER.Subsystem] == 'IMAGE_SUBSYSTEM_WINDOWS_GUI':
                # We only return true if all went well
                result = True
        except pefile.PEFormatError, e:
            # There's not much we can do if pefile fails
            pass

        m.close()
        os.close(fd)
    except Exception, e:
        # Not much we can do for exceptions
        pass

    # Return False when not sure
    return result

def apply_settings(settings_file):
    """
    Execute a configuration file (if it exists), overriding values from the
    global configuration objects (created when this module is loaded)
    """
    if os.path.exists(settings_file):
        try:
            # We initialize the dictionary to readily contain the settings
            # structures; anything else needs to be explicitly imported
            execfile(settings_file, dict(pycmd_public.__dict__.items() + [('__file__', settings_file)]))
        except Exception, e:
            print 'Error encountered when loading ' + settings_file
            print 'Subsequent settings will NOT be applied!'
            traceback.print_exc()

def sanitize_settings():
    """Sanitize all the configuration instances"""
    pycmd_public.appearance.sanitize()
    pycmd_public.behavior.sanitize()
