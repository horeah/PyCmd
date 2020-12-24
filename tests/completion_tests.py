#
# Unit tests for completion.py
#

from unittest import TestCase, TestSuite, defaultTestLoader
from completion import wildcard_to_regex, find_common_prefix

class TestWildcardMatching(TestCase):
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

    def test_wildcard_matching(self):
        """Test the matching and grouping of shell patterns"""
        for name, pattern, groups in self.matches:
            result = wildcard_to_regex(pattern).match(name)
            if result != None:
                self.assertEqual(result.groups(), groups)
            else:
                self.assertEqual(None, groups)


class TestFindCommonPrefix(TestCase):
    results = [
        ('prog', ['program', 'program2', 'programme'], 'program'),
        ('Prog', ['program', 'program2', 'programme'], 'program'),
        ('Prog', ['Program', 'Program2', 'Programme'], 'Program'),
        ('prog', ['PrOgram', 'Program2', 'PrOgramme'], 'PrOgram'),
        ('prog', ['PROGRAM', 'Program2', 'programme'], 'program'),
        ('sys', ['System', 'System32', 'system.ini'], 'system'),
        ('C:\\Windows\\sys',  ['System', 'System32', 'system.ini'], 'System'),
        ]

    def test_find_common_prefix(self):
        """Test the computation of a common prefix"""
        for original, completions, result in self.results:
            self.assertEqual(find_common_prefix(original, completions), result)


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestWildcardMatching))
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestFindCommonPrefix))
    return suite
