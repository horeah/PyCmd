"""
Public utilities exported by PyCmd.

These are meant to be used in init.py files; users can rely on them being kept
unchanged (interface-wise) throughout later versions.
"""
import os, sys, common

def abbrev_path(path):
    """
    Abbreviate a full path to make it shorter, yet still unambiguous.

    This function takes a directory path and tries to abbreviate it as much as
    possible while making sure that the resulting shortened path is not
    ambiguous: a path element is only abbreviated if its shortened form is
    unique in its directory (in other words, if a sybling would have the same
    abbreviation, the original name is kept).

    The abbreviation is performed by keeping only the first letter of each
    "word" composing a path element. "Words" are defined by CamelCase,
    underscore_separation or "whitespace separation".
    """
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
    curdir = os.getcwd().decode(sys.getfilesystemencoding())
    curdir = curdir[0].upper() + curdir[1:]
    return abbrev_path(curdir) + u'> '


