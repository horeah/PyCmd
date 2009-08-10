#
# Common utility functions
#
import os, string, fsm

# Command splitting characters
sep_chars = ['|', '&', '>', '<']

# Comand sequencing tokens
seq_tokens = ['||', '&', '&&']

# Redirection tokens
digit_chars = [chr(ord('0') + i) for i in range(10)]
redir_file_simple = ['>', '>>', '<']
redir_file_tokens = redir_file_simple + [d + c for d in digit_chars for c in redir_file_simple]
# print redir_pipe_tokens + redir_file_tokens

# All command splitting tokens
sep_tokens = seq_tokens + ['|'] + redir_file_tokens

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

    f.add_transition_list(string.whitespace, 'init', start_empty_token, 'whitespace')
    f.add_transition('"', 'init', accumulate, 'in_string')
    f.add_transition('|', 'init', start_token, 'pipe')
    f.add_transition('&', 'init', start_token, 'amp')
    f.add_transition('>', 'init', start_token, 'gt')
    f.add_transition('<', 'init', accumulate_last, 'init')
    f.add_transition_any('init', accumulate, 'init')

    f.add_transition_list(string.whitespace, 'whitespace', None, 'whitespace')
    f.add_transition_list(string.digits, 'whitespace', accumulate, 'redir')
    f.add_empty_transition('whitespace', 'init')

    f.add_transition('"', 'in_string', accumulate, 'init')
    f.add_transition_any('in_string', accumulate, 'in_string')

    f.add_transition('|', 'pipe', accumulate_last, 'init')
    f.add_empty_transition('pipe', 'init', start_empty_token)

    f.add_transition('&', 'amp', accumulate_last, 'init')
    f.add_empty_transition('amp', 'init', start_empty_token)

    f.add_transition('>', 'gt', accumulate_last, 'init')
    f.add_empty_transition('gt', 'init', start_empty_token)

    f.add_transition('<', 'redir', accumulate_last, 'init')
    f.add_transition('>', 'redir', accumulate, 'redir2')
    f.add_empty_transition('redir', 'init')

    f.add_transition('>', 'redir2', accumulate_last, 'init')
    f.add_empty_transition('redir2', 'init', start_empty_token)

    f.process_list(line)
    if len(f.memory) > 0 and f.memory[-1] == '':
        del f.memory[-1]

    return f.memory


def expand_env_vars(string):
    """Return a version of the string with the environment variables expanded"""
    # Expand tilde to %HOME% or %USERPROFILE%
    if 'HOME' in os.environ.keys():
        home_var = 'HOME'
    else:
        home_var = 'USERPROFILE'

    if string.startswith('~') or string.startswith('"~'):
        string = string.replace('~', '%' + home_var + '%', 1)

    # Expand all %variable%s
    begin = string.find('%')
    while begin >= 0:
        end = string.find('%', begin + 1)
        if end >= 0:
            # Found a %variable%
            var = string[begin:end].strip('%')
            if var in os.environ.keys():
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


def abbrev_path(path):
    """Abbreviate a full path to make it shorter, yet still unambiguous"""
    current_dir = path[ : 3]
    path = path[3 : ]
    path_abbrev = current_dir[ : 2]

    for elem in path.split('\\')[ : -1]:
        elem_abbrev = abbrev_string(elem)
        for other in os.listdir(current_dir):
            if os.path.isdir(current_dir + '\\' + other) and abbrev_string(other).lower() == elem_abbrev.lower() and other.lower() != elem.lower():
                # Found other directory with the same abbreviation
                # In this case, we use the entire name
                elem_abbrev = elem
                break
        current_dir += '\\' + elem
        path_abbrev += '\\' + elem_abbrev

    return path_abbrev + '\\' + path.split('\\')[-1]


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
    """Check whether the specified file is executable, i.e. its extension is .exe, .com or .bat"""
    return file_name.endswith('.com') or file_name.endswith('.exe') or file_name.endswith('.bat')

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
