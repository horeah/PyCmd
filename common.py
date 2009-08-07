#
# Common utility functions
#
import os

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
    tokens = []
    current = ''
    within_quotes = False
    for char in line:
        if char == '"':
            within_quotes = not within_quotes
            current += char
        else:
            if within_quotes:
                current += char
            else:
                if char == ' ':
                    tokens.append(current)
                    current = ''
                elif char == '|':
                    if current == '|':
                        tokens.append('||')
                        current = ''
                    else:
                        tokens.append(current)
                        current = char
                elif char in sep_chars:
                    if current in digit_chars or current in sep_tokens:
                        if current + char in sep_tokens:
                            current += char
                        else:
                            tokens.append(current)
                            current = char
                    else:
                        tokens.append(current)
                        current = char
                else:
                    if current in sep_tokens:
                        tokens.append(current)
                        current = char
                    else:
                        current += char

    while '' in tokens:
        tokens.remove('')
    tokens.append(current)
    if current in sep_tokens:
        tokens.append('')
    # print '\n\n', tokens, '\n\n'
    return tokens


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
