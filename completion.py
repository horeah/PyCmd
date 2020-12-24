#
# Functions useful for completing:
#    1) names of files and directories
#    2) names of environment variables
#

import sys, os, re
from common import tokenize, expand_env_vars, has_exec_extension, strip_extension
from common import contains_special_char, starts_with_special_char
from common import sep_chars, seq_tokens

def complete_file(line):
    """
    Complete names of files and/or directories

    This tokenizes the current line using two approaches in turn, trying to
    suggest valid completions in each case.
    
    The two approaches are:
      1) A simple white-space based tokenization as required in most situations
      2) If 1 yields no completions, try to treat the last argument as a
      semicolon-separated list of paths, optionally preceeded by an equal
      character

      The return value is a tuple containing 
       a) the updated line (includes the completed suffix and quotes if needed) 
       b) and a list of possible subsequent completions
    """
    (completed, completions) = complete_file_simple(line)
    if completed == line and completions == []:
        # Try the alternate completion
        (completed, completions) = complete_file_alternate(line)

    return (completed, completions)

def complete_file_simple(line):
    """
    Complete names of files or directories
    This function tokenizes the line and computes file and directory
    completions starting with the last token.
    
    It returns a pair:
      - the line expanded up to the longest common sequence among the
        completions
      - the list of all possible completions (first dirs, then files)
    """
    tokens = tokenize(line)
    token = tokens[-1].replace('"', '')

    pos_fwd = expand_env_vars(token).rfind('/')
    pos_bck = expand_env_vars(token).rfind('\\')
    path_sep = '\\' if pos_bck >= pos_fwd else '/'
    
    (path_to_complete, _, prefix) = token.rpartition(path_sep)
    if path_to_complete == '' and token != '' and token[0] == path_sep:
        path_to_complete = path_sep

    # print '\n\n', path_to_complete, '---', prefix, '\n\n'

    if path_to_complete == '':
        dir_to_complete = os.getcwd()
    elif path_to_complete == path_sep:
        dir_to_complete = os.getcwd()[0:3]
    else:
        dir_to_complete = expand_env_vars(path_to_complete) + path_sep

    # This is the wildcard matcher used throughout the function
    matcher = wildcard_to_regex(prefix + '*')

    completions = []
    if os.path.isdir(dir_to_complete):
        try:
            completions = [elem for elem in os.listdir(dir_to_complete) 
                           if matcher.match(elem)]
        except OSError:
            # Cannot complete, probably access denied
            pass
        

    # Sort directories first, also append '\'; then, files
    completions_dirs = [elem + path_sep for elem in completions if os.path.isdir(dir_to_complete + path_sep + elem)]
    completions_files = [elem for elem in completions if os.path.isfile(dir_to_complete + path_sep + elem)]
    completions = completions_dirs + completions_files

    if (len(tokens) == 1 or tokens[-2] in seq_tokens) and path_to_complete == '':
        # We are at the beginning of a command ==> also complete from the path
        completions_path = []
        for elem_in_path in os.environ['PATH'].split(';'):
            dir_to_complete = expand_env_vars(elem_in_path) + path_sep
            try:                
                completions_path += [elem for elem in os.listdir(dir_to_complete) 
                                     if matcher.match(elem)
                                     and os.path.isfile(dir_to_complete + path_sep + elem)
                                     and has_exec_extension(elem)
                                     and not elem in completions
                                     and not elem in completions_path]
            except OSError:
                # Cannot complete, probably access denied
                pass

        # Add internal commands
        internal_commands = ['assoc',
                             'call', 'cd', 'chdir', 'cls', 'color', 'copy',
                             'date', 'del', 'dir',
                             'echo', 'endlocal', 'erase', 'exit',
                             'for', 'ftype',
                             'goto',
                             'if',
                             'md', 'mkdir', 'move',
                             'path', 'pause', 'popd', 'prompt', 'pushd',
                             'rem', 'ren', 'rename', 'rd', 'rmdir',
                             'set', 'setlocal', 'shift', 'start',
                             'time', 'title', 'type',
                             'ver', 'verify', 'vol']
        if sys.getwindowsversion()[0] >= 6:
            # Windows 7 or newer
            internal_commands.append('mklink')
        completions_path += [elem for elem in internal_commands
                             if matcher.match(elem)
                             and not elem in completions
                             and not elem in completions_path]


        # Sort in lexical order (case ignored)
        completions_path.sort(key=str.lower)

        # Remove .com, .exe or .bat extension where possible
        completions_path_no_ext = [strip_extension(elem) for elem in completions_path]
        completions_path_nice = []
        for i in range(0, len(completions_path_no_ext)):
            similar = [elem for elem in completions_path_no_ext if elem == completions_path_no_ext[i]]
            similar += [elem for elem in completions if strip_extension(elem) == completions_path_no_ext[i]]
            if len(similar) == 1 and has_exec_extension(completions_path[i]) and len(prefix) < len(completions_path[i]) - 3:
                # No similar executables, don't use extension
                completions_path_nice.append(completions_path_no_ext[i])
            else:
                # Similar executables found, keep extension
                completions_path_nice.append(completions_path[i])
        completions += completions_path_nice

    if completions != []:
        # Find the longest common sequence
        common_string = find_common_prefix(prefix, completions)
            
        if path_to_complete == '':
            completed_file = common_string
        elif path_to_complete == path_sep:
            completed_file = path_sep + common_string
        else:
            completed_file = path_to_complete + path_sep + common_string

        if expand_env_vars(completed_file).find(' ') >= 0 or \
                (prefix != '' and [elem for elem in completions if contains_special_char(elem)] != []) or \
                (prefix == '' and [elem for elem in completions if starts_with_special_char(elem)] != []):
            # We add quotes if one of the following holds:
            #   * the (env-expanded) completed string contains whitespace
            #   * there is a prefix and at least one of the valid completions contains whitespace
            #   * there is no prefix and at least one completion _starts_ with whitespace
            start_quote = '"'
        else:
            start_quote = ''

        # Build the result
        result = line[0 : len(line) - len(tokens[-1])] + start_quote + completed_file

        if len(completions) == 1:
            # We can close the quotes if we have completed to a unique filename
            if start_quote == '"':
                end_quote = '"'
            else:
                end_quote = ''
                
            if result[-1] == path_sep:
                # Directory -- we want the backslash (if any) AFTER the closing quote
                result = result[ : -1] + end_quote + path_sep
            else:
                # File -- add space if the completion is unique
                result += end_quote
                result += ' '

        return (result, completions)
    else:
        # No expansion was made, return original line
        return (line, [])


def complete_file_alternate(line):
    """
    Complete names of files or directories using an alternate tokenization

    This function tokenizes the line by tring to interpret the last token as a
    semicolon-separated list of paths, optionally preceded by an equals char.
    
    It returns a pair:
      - the line expanded up to the longest common sequence among the
        completions
      - the list of all possible completions (first dirs, then files)
    """
    tokens = tokenize(line)
    (last_token_prefix, equal_char, last_token) = tokens[-1].replace('"', '').rpartition('=')
    last_token_prefix += equal_char
        
    paths = last_token.split(';')
    token = paths[-1]

    path_sep = '/' if '/' in expand_env_vars(token) else '\\'

    # print '\n\nTokens:', tokens, '\n\nCompleting:', token, '\n\n'

    (path_to_complete, _, prefix) = token.rpartition(path_sep)
    if path_to_complete == '' and token != '' and token[0] == path_sep:
        path_to_complete = path_sep

    # print '\n\n', path_to_complete, '---', prefix, '\n\n'

    if path_to_complete == '':
        dir_to_complete = os.getcwd()
    elif path_to_complete == path_sep:
        dir_to_complete = os.getcwd()[0:3]
    else:
        dir_to_complete = expand_env_vars(path_to_complete) + path_sep

    # This is the wildcard matcher used throughout the function
    matcher = wildcard_to_regex(prefix + '*')

    completions = []
    if os.path.isdir(dir_to_complete):
        try:
            completions = [elem for elem in os.listdir(dir_to_complete) 
                           if matcher.match(elem)]
        except OSError:
            # Cannot complete, probably access denied
            pass
        

    # Sort directories first, also append '\'; then, files
    completions_dirs = [elem + path_sep for elem in completions if os.path.isdir(dir_to_complete + path_sep + elem)]
    completions_files = [elem for elem in completions if os.path.isfile(dir_to_complete + path_sep + elem)]
    completions = completions_dirs + completions_files

    if completions != []:
        # Find the longest common sequence
        common_string = find_common_prefix(prefix, completions)
            
        if path_to_complete == '':
            completed_file = common_string
        elif path_to_complete == path_sep:
            completed_file = path_sep + common_string
        else:
            completed_file = path_to_complete + path_sep + common_string

        if expand_env_vars(last_token + completed_file).find(' ') >= 0 or \
                (prefix != '' and [elem for elem in completions if contains_special_char(elem)] != []) or \
                (prefix == '' and [elem for elem in completions if starts_with_special_char(elem)] != []):
            # We add quotes if one of the following holds:
            #   * the (env-expanded) completed string contains whitespace
            #   * there is a prefix and at least one of the valid completions contains whitespace
            #   * there is no prefix and at least one completion _starts_ with whitespace
            start_quote = '"'
        else:
            start_quote = ''

        # Build and return the result
        result = line[0 : len(line) - len(tokens[-1])]
        result += last_token_prefix + start_quote
        result += last_token[:len(last_token) - len(token)]
        result += completed_file
        return (result, completions)
    else:
        # No expansion was made, return original line
        return (line, [])


def complete_wildcard(line):
    """
    Complete file/dir wildcards
    This function tokenizes the line and computes file and directory
    completions starting with the last token which is a wildcard
    
    It returns a pair:
      - the line expanded up to the longest common sequence among the
        completions
      - the list of all possible completions (first dirs, then files)
    """
    tokens = tokenize(line)
    token = tokens[-1].replace('"', '')

    path_sep = '/' if '/' in expand_env_vars(token) else '\\'
    
    (path_to_complete, _, prefix) = token.rpartition(path_sep)
    if path_to_complete == '' and token != '' and token[0] == path_sep:
        path_to_complete = path_sep

    # print '\n\n', path_to_complete, '---', prefix, '\n\n'

    if path_to_complete == '':
        dir_to_complete = os.getcwd()
    elif path_to_complete == path_sep:
        dir_to_complete = os.getcwd()[0:3]
    else:
        dir_to_complete = expand_env_vars(path_to_complete) + path_sep

    # This is the wildcard matcher used throughout the function
    matcher = wildcard_to_regex(prefix + '*')

    completions = []
    if os.path.isdir(dir_to_complete):
        try:
            completions = [elem for elem in os.listdir(dir_to_complete) if matcher.match(elem)]
        except OSError:
            # Cannot complete, probably access denied
            pass


    # Sort directories first, also append '\'; then, files
    completions_dirs = [elem + path_sep for elem in completions if os.path.isdir(dir_to_complete + path_sep + elem)]
    completions_files = [elem for elem in completions if os.path.isfile(dir_to_complete + path_sep + elem)]
    completions = completions_dirs + completions_files

    if completions != []:
        completed_suffixes = []
        for c in completions:
            match = matcher.match(c)
            completed_suffixes.append(match.group(match.lastindex))

        if len(completions) == 1:
            # Only one match, we can inline it and replace the wildcards
            common_string = completions[0]
        else:
            # Multiple matches, find the longest common sequence
            common_string = prefix + find_common_prefix(prefix, completed_suffixes)
            
        if path_to_complete == '':
            completed_file = common_string
        elif path_to_complete == path_sep:
            completed_file = path_sep + common_string
        else:
            completed_file = path_to_complete + path_sep + common_string


        if expand_env_vars(completed_file).find(' ') >= 0 or \
                (prefix != '' and [elem for elem in completions if contains_special_char(elem)] != []) or \
                (prefix == '' and [elem for elem in completions if starts_with_special_char(elem)] != []):
            # We add quotes if one of the following holds:
            #   * the (env-expanded) completed string contains whitespace
            #   * there is a prefix and at least one of the valid completions contains whitespace
            #   * there is no prefix and at least one completion _starts_ with whitespace
            start_quote = '"'
        else:
            start_quote = ''

        # Build the result
        result = line[0 : len(line) - len(tokens[-1])] + start_quote + completed_file
        if len(completions) == 1 or \
                not common_string.endswith('*') and \
                max([len(c) for c in completed_suffixes]) == len(common_string) - len(prefix):
            # We can close the quotes if all the completions have the same suffix or 
            # there exists only one matching file
            if start_quote == '"':
                end_quote = '"'
            else:
                end_quote = ''
                
            if result[-1] == path_sep:
                # Directory -- we want the backslash (if any) AFTER the closing quote
                result = result[ : -1] + end_quote + path_sep
            else:
                # File -- add space if the completion is unique
                result += end_quote
                result += ' '

        return (result, completions)
    else:
        # No expansion was made, return original line
        return (line, [])


def complete_env_var(line):
    """
    Complete names of environment variables
    This function tokenizes the line and computes completions
    based on environment variables starting with the last token
    
    It returns a pair:
      - the line expanded up to the longest common sequence among the
        completions
      - the list of all possible completions
    """
    tokens = tokenize(line)

    # Account for the VAR=VALUE syntax
    (token_prefix, equals, token_orig) = tokens[-1].rpartition('=')
    token_prefix += equals

    if token_orig.count('%') % 2 == 0 and token_orig.strip('"').endswith('%'):
        [lead, prefix] = token_orig.strip('"').rstrip('%').rsplit('%', 2)
    else:
        [lead, prefix] = token_orig.strip('"').rsplit('%', 1)

    if token_orig.strip('"').endswith('%') and prefix != '':
        completions = [prefix]
    else:
        completions = [var for var in os.environ if var.lower().startswith(prefix.lower())]

    completions.sort()

    if completions != []:
        # Find longest prefix
        common_string = find_common_prefix(prefix, completions)
        
        quote = ''  # Assume no quoting needed by default, then check for spaces
        for completion in completions:
            if contains_special_char(os.environ[completion]):
                quote = '"'
                break
            
        result = line[0 : len(line) - len(token_orig)] + quote + lead + '%' + common_string
        
        if len(completions) == 1:
            result += '%' + quote
            return (result, [result])
        else:
            return (result, completions)
    else:
        # No completion possible, return original line
        return (line, [])



def find_common_prefix(original, completions):
    """
    Search for the longest common prefix in a list of strings
    Returns the longest common prefix
    """
    common_len = 0
    common_string = ''
    mismatch = False
    perfect = True

    # Cache lowercase version to avoid repeated calls to str.lower()
    completions_lower = [s.lower() for s in completions]
    common_string_lower = ''

    while common_len < len(completions[0]) and not mismatch:
        common_len += 1
        common_string = completions[0][0:common_len]
        common_string_lower = completions_lower[0][0:common_len]
        for i in range(1, len(completions)):
            completion = completions[i]
            completion_lower = completions_lower[i]
            if completion_lower[0:common_len] != common_string_lower:
                mismatch = True
            elif completion[0:common_len] != common_string:
                perfect = False
    if mismatch:
        common_string = common_string[:-1]
        common_len -= 1

    # Try to take a good guess wrt letter casing
    if not perfect:
        for i in range(len(original)):
            case_match = [c for c in completions if c.startswith(original[:i + 1])]
            if len(case_match) > 0:
                common_string = case_match[0][:common_len]
            else:
                break

    return common_string


def wildcard_to_regex(pattern):
    """
    Transform a wildcard pattern into a compiled regex object.
    This also handles escaping as needed.    
    """
    # Transform pattern into regexp
    translations = [('\\', '\\\\'),
                    ('(', '\\('), 
                    (')', '\\)'),
                    ('[', '\\['), 
                    (']', '\\]'),
                    ('.', '\\.'),
                    ('+', '\\+'),
                    ('^', '\\^'),
                    ('$', '\\$'),
                    ('?', '(.)'), 
                    ('*', '(.*)')]
                    
    re_pattern = pattern
    for src, dest in translations:
        re_pattern = re_pattern.replace(src, dest)
    re_pattern += '$'
    return re.compile(re_pattern, re.IGNORECASE)


def has_wildcards(pattern):
    """Check if the given pattern contains wildcards"""
    return pattern.find('*') >= 0 or pattern.find('?') >= 0
