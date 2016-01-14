#
# Unit tests for console.py
#

from unittest import TestCase, TestSuite, defaultTestLoader
from InputState import InputState

class TestInputState(TestCase):
    """Test the handling of key_complete"""

    def setUp(self):
        self.state = InputState()

    def testBasicCompletion(self):
        """Test the basic insertion of completed contend in current command"""
        self.state.before_cursor = 'C:\\'
        self.state.key_complete('C:\\Windows')
        self.assertEqual(self.state.before_cursor, 'C:\\Windows')
        self.assertEqual(self.state.after_cursor, '')

    def testAvoidDuplicateFillers(self):
        """Tests the avoidance of duplicate whitespace, backslash, quites after completing"""
        self.state.before_cursor = '"c:\\Program Files (x86)\\Sysinternals Suite'
        self.state.after_cursor = '"\\'
        self.state.key_complete('"c:\\Program Files (x86)\\Sysinternals Suite"\\')
        self.assertEquals(self.state.before_cursor, '"c:\\Program Files (x86)\\Sysinternals Suite"\\')
        self.assertEquals(self.state.after_cursor, '')

        self.state.before_cursor = '"c:\\Program Files (x86)\\Sysinternals Suite'
        self.state.after_cursor = '"\\'
        self.state.key_complete('"c:\\Program Files (x86)\\Sysinternals Suite\\ProcFeatures.exe" ')
        self.assertEqual(self.state.before_cursor, '"c:\\Program Files (x86)\\Sysinternals Suite\\ProcFeatures.exe" ')
        self.assertEqual(self.state.after_cursor, '')

def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestInputState))
    return suite

