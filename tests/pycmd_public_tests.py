from unittest import TestCase, TestSuite, defaultTestLoader
from pycmd_public import abbrev_path
from os.path import join, expanduser

class TestAbbrevPath(TestCase):
    def testAbbrevPath(self):
        assert abbrev_path(expanduser('~')) == '~'
        assert abbrev_path(expanduser('~').lower()) == '~'
        assert abbrev_path(expanduser(join('~', 'some_dir')) == join('~', 'some_dir'))
        
        sys32_abbrev_elems = abbrev_path(r'C:\Windows\system32').split('\\')
        assert(len(sys32_abbrev_elems) == 3)
        assert(sys32_abbrev_elems[0] == 'C:')
        assert(sys32_abbrev_elems[1].startswith('W'))
        assert(sys32_abbrev_elems[2] == 'system32')

        assert(abbrev_path('C:\\') == 'C:\\')


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestAbbrevPath))
    return suite
