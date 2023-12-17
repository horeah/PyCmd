#
# Unit tests for executing commands
#

from unittest import TestCase, TestSuite, defaultTestLoader
import PyCmd
from common import expand_env_vars
import os, time

test_dir = os.path.split(__file__)[0]
orig_cwd = os.getcwd()
PyCmd.tmpfile = os.path.join(test_dir, 'tmpfile')
prev_path = os.environ['PATH']

class TestDelayedExpansion(TestCase):
    def setUp(self):
        PyCmd.behavior.delayed_expansion = True
        os.environ['ERRORLEVEL'] = '0'
        
    def testExternalCommand(self):
        PyCmd.run_command(['ipconfig', '>NUL'])
        self.assertEqual(os.environ['ERRORLEVEL'], '0')

    def testInternalCommand(self):
        PyCmd.run_command(['dir', '>NUL'])
        self.assertEqual(os.environ['ERRORLEVEL'], '0')

    def testInexistentCommand(self):
        PyCmd.run_command(['inexistent_command.exe', '2>NUL'])
        self.assertEqual(os.environ['ERRORLEVEL'], '9009')

    def testGuiApplication(self):
        PyCmd.run_command(['msg.exe', '/TIME:1', '*', 'waiting one second'])
        self.assertEqual(os.environ['ERRORLEVEL'], '0')
        time.sleep(3)

    def testInternalCd(self):
        PyCmd.run_command(['cd', '..'])
        self.assertEqual(os.environ['CD'], os.path.abspath(os.path.join(orig_cwd, '..')))
        self.assertEqual(os.environ['ERRORLEVEL'], '0')
        os.chdir(orig_cwd)
        
    def testInternalCdNoArgs(self):
        PyCmd.run_command(['cd'])
        self.assertEqual(os.environ['CD'], expand_env_vars('~'))
        self.assertEqual(os.environ['ERRORLEVEL'], '0')
        os.chdir(orig_cwd)

    def testInternalCdInexistent(self):
        PyCmd.run_command(['cd', 'inexistent_dir'])
        self.assertEqual(os.environ['CD'], orig_cwd)
        self.assertEqual(os.environ['ERRORLEVEL'], '1')

    def testExternalCd(self):
        PyCmd.run_command(['cd', '..', '&&', 'echo Hi', '>NUL'])
        self.assertEqual(os.environ['CD'], os.path.abspath(os.path.join(orig_cwd, '..')))
        self.assertEqual(os.environ['ERRORLEVEL'], '0')

    def testExternalCdInexistent(self):
        PyCmd.run_command(['cd', 'inexistent_dir', '2>', 'NUL'])
        self.assertEqual(os.environ['CD'], orig_cwd)
        self.assertEqual(os.environ['ERRORLEVEL'], '1')

    def testPushd(self):
        PyCmd.run_command(['pushd', '..'])
        self.assertEqual(os.environ['CD'], os.path.abspath(os.path.join(orig_cwd, '..')))
        PyCmd.run_command(['popd'])
        self.assertEqual(os.environ['CD'], os.path.abspath(os.path.join(orig_cwd)))

    def testBrokenPath(self):
        os.environ['PATH'] = 'Wrong stuff'
        PyCmd.run_command(['dir', '>NUL'])
        self.assertEqual(os.environ['ERRORLEVEL'], '0')
        PyCmd.run_command(['ipconfig', '2>NUL'])
        self.assertEqual(os.environ['ERRORLEVEL'], '9009')
        
    def tearDown(self):
        os.chdir(orig_cwd)
        if os.path.isfile(PyCmd.tmpfile):
            os.remove(PyCmd.tmpfile)
        os.environ['PATH'] = prev_path
        del os.environ['ERRORLEVEL']


class TestNoDelayedExpansion(TestCase):
    def setUp(self):
        PyCmd.behavior.delayed_expansion = False
        if 'ERRORLEVEL' in os.environ:
            del os.environ['ERRORLEVEL']
        
    def testExternalCommand(self):
        PyCmd.run_command(['ipconfig', '>NUL'])

    def testInternalCommand(self):
        PyCmd.run_command(['dir', '>NUL'])

    def testInexistentCommand(self):
        PyCmd.run_command(['inexistent_command.exe', '2>NUL'])

    def testGuiApplication(self):
        PyCmd.run_command(['msg.exe', '/TIME:1', '*', 'waiting one second'])
        time.sleep(3)

    def testInternalCd(self):
        PyCmd.run_command(['cd', '..'])
        self.assertEqual(os.environ['CD'], os.path.abspath(os.path.join(orig_cwd, '..')))
        os.chdir(orig_cwd)

    def testInternalCdInexistent(self):
        PyCmd.run_command(['cd', 'inexistent_dir'])
        self.assertEqual(os.environ['CD'], orig_cwd)

    def testExternalCd(self):
        PyCmd.run_command(['cd', '..', '&&', 'echo Hi', '>NUL'])
        self.assertEqual(os.environ['CD'], os.path.abspath(os.path.join(orig_cwd, '..')))

    def testExternalCdInexistent(self):
        PyCmd.run_command(['cd', 'inexistent_dir', '2>', 'NUL'])
        self.assertEqual(os.environ['CD'], orig_cwd)

    def testBrokenPath(self):
        os.environ['PATH'] = 'Wrong stuff'
        PyCmd.run_command(['dir', '>NUL'])
        PyCmd.run_command(['ipconfig', '2>NUL'])


    def tearDown(self):
        os.chdir(orig_cwd)
        if os.path.isfile(PyCmd.tmpfile):
            os.remove(PyCmd.tmpfile)
        os.environ['PATH'] = prev_path


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestDelayedExpansion))
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestNoDelayedExpansion))
    return suite
