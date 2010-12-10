#
# Unit tests for completion.py
#

import unittest
from completion import fnmatch

class TestFnmatch(unittest.TestCase):
    matches = [
        ('abc', 'abc', ()),
        ('abc', 'ab?', ('c',)),
        ('abc', 'a*', ('bc',)),
        ('abcde', '?bc*', ('a', 'de')),
        ('abcde', '?bcde*', ('a', '')),
        ('abc', 'abd', None),
        ('c:\\program files', 'c:\\p*', ('rogram files',)),
        ('a.c', 'a?.c', None),
        ('test.py', '*est.*', ('t', 'py')),
        ('test.pyc', '*.py', None),
        ('a(b)', 'a(*', ('b)',)),
        ('abc[2]', 'a*[', None),
        ('abc[2]', 'a*[*', ('bc', '2]')),
        ]

    def test_fnmatch(self):
        """Test the matching and grouping of shell patterns"""
        for name, pattern, groups in self.matches:
            result = fnmatch(name, pattern)
            if result != None:
                self.assertEqual(result.groups(), groups)
            else:
                self.assertEqual(None, groups)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestFnmatch)
