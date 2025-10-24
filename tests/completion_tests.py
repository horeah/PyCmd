#
# Unit tests for completion.py
#

import sys
from unittest import TestCase, TestSuite, defaultTestLoader
from completion import wildcard_to_regex, find_common_prefix, adjust_completion

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

class TestAdjustCompletion(TestCase):
    results_win = [
        # (completed, after, unique) (completed, after)
        (('C:\\Windows\\', '', True), ('C:\\Windows\\', '')),
        (('C:\\Windows\\', '\\System32', True), ('C:\\Windows\\', 'System32')),
        (('C:\\Windows\\', 'ows\\', True), ('C:\\Windows\\', '')),
        (('C:\\Windows\\', 'ows', True), ('C:\\Windows\\', '')),
        (('PyCmd-20250906-w32.zip', '.zip', True), ('PyCmd-20250906-w32.zip ', '')),
        (('"C:\\Program Files', 'Files\\', False), ('"C:\\Program Files', '\\')),
        (('"C:\\Program Files (x86)\\', '86)\\Microsoft', True), ('"C:\\Program Files (x86)\\', 'Microsoft')),
        (('dirname','Users', True), ('dirname ', 'Users')),
        (('"%PROGRAMFILES%', '', True), ('"%PROGRAMFILES%"\\', '')),
        (('"%PROGRAMFILES', '', True), ('"%PROGRAMFILES%"\\', '')),
        (('"%PROGRAMFILES', '', False), ('"%PROGRAMFILES', '')),
        (('copy file1.txt', '.txt C:\\Users', True), ('copy file1.txt ', 'C:\\Users')),
        (('set PATH=%PATH', '', False), ('set PATH=%PATH', '')),
        (('ls "C:\\Program Files\\7-Zip\\', 'Zip"\\', True), ('ls "C:\\Program Files\\7-Zip"\\', '')),
        (('ls "C:\\Windows\\', '', True), ('ls C:\\Windows\\', '')),
        (('ls "~\\Desktop\\', '', True), ('ls ~\\Desktop\\', '')),
        (('ls "~\\with space\\', '', True), ('ls "~\\with space"\\', '')),
    ]

    results_linux = [
        # (completed, after, unique) (completed, after)
        (('/usr/bin/', '', True), ('/usr/bin/', '')),
        (('/usr/bin/', 'python3', True), ('/usr/bin/', 'python3')),
        (('/usr/bin/', 'n/python3', True), ('/usr/bin/', 'python3')),
        (('/usr/bin/', 'n', True), ('/usr/bin/', '')),
        (('file.tar.gz', '.tar.gz', True), ('file.tar.gz ', '')),
        (('$HOME', '', True), ('$HOME/', '')),
        (('${HOME', '', True), ('${HOME}/', '')),
        (('$BASH_VERSION', '', True), ('$BASH_VERSION ', '')),
        (('cp file1.txt', '.txt ~/docs', True), ('cp file1.txt ', '~/docs')),
        (('export PATH=${PATH', '', False), ('export PATH=${PATH', '')),
        (('echo "${PATH', '', True), ('echo "${PATH}" ', '')),
        (('ls "/mnt/c/Program Files/7-Zip/', 'Zip"/', True), ('ls "/mnt/c/Program Files/7-Zip"/', '')),
        (('ls "/mnt/c/Windows/', '', True), ('ls /mnt/c/Windows/', '')),
        (('ls "~/work/', '', True), ('ls ~/work/', '')),
        (('ls "~/with space/', '', True), ('ls ~/"with space"/', '')),
    ]

    results = results_win if sys.platform == 'win32' else results_linux

    def test_adjust_completion(self):
        """Test adjustment after completion"""
        for input, output in self.results:
            self.assertEqual(adjust_completion(*input), output)


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestWildcardMatching))
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestFindCommonPrefix))
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestAdjustCompletion))
    return suite
