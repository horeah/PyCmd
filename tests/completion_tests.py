#
# Unit tests for completion.py
#

import unittest
from completion import fnmatch

class TestFnmatch(unittest.TestCase):
    matches_true = [
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
        ]

    def test_fnmatch(self):
        """Test the matching and grouping of shell patterns"""
        for name, pattern, groups in self.matches_true:
            result = fnmatch(name, pattern)
            if result != None:
                self.assertEqual(result.groups(), groups)
            else:
                self.assertEqual(None, groups)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestFnmatch)
