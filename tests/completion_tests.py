#
# Unit tests for completion.py
#

import unittest
from completion import wildcard_to_regex

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
        ('a+b', 'a++', None),
        ('a++b', 'a+*', ('+b',)),
        ('c^ab', '*^*b', ('c', 'a')),
        ('c$ab', '*$*b', ('c', 'a')),
        ]

    def test_fnmatch(self):
        """Test the matching and grouping of shell patterns"""
        for name, pattern, groups in self.matches:
            result = wildcard_to_regex(pattern).match(name)
            if result != None:
                self.assertEqual(result.groups(), groups)
            else:
                self.assertEqual(None, groups)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestFnmatch)
