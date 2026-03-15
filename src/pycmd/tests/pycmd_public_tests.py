import sys
from unittest import TestCase, TestSuite, defaultTestLoader
from pycmd_public import abbrev_path
from os.path import join, expanduser
import getpass

class TestAbbrevPath(TestCase):
    def testAbbrevPath(self):
        assert abbrev_path(expanduser('~')) == '~'
        assert abbrev_path(expanduser('~').lower()) == '~'
        assert abbrev_path(expanduser(join('~', 'some_dir')) == join('~', 'some_dir'))

        if sys.platform == 'win32':        
            sys32_abbrev_elems = abbrev_path(r'C:\Windows\system32').split('\\')
            assert(len(sys32_abbrev_elems) == 3)
            assert(sys32_abbrev_elems[0] == 'C:')
            assert(sys32_abbrev_elems[1].startswith('W'))
            assert(sys32_abbrev_elems[2] == 'system32')

            assert(abbrev_path('C:\\') == 'C:\\')

            # Listing C:\Documents and Settings is not allowed
            userdir = f'C:\\Documents and Settings\\{getpass.getuser()}'
            userdir_abbrev = f'C:\\DaS\\{getpass.getuser()}'
            assert(abbrev_path(userdir) == userdir_abbrev)
            assert(abbrev_path(userdir + r'\somedir') == userdir_abbrev + r'\somedir')
        else:
            assert abbrev_path('/') == '/'
            assert abbrev_path('/usr') == '/usr'
            assert abbrev_path('/usr/bin') == '/u/bin'
            assert abbrev_path('/usr/lib/something') == '/u/lib/something'
            assert(abbrev_path('/usr/lib64/something')) == '/u/l64/something'

def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestAbbrevPath))
    return suite
