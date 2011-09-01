#
# Unit tests for PyCmd.py
#

import os, tempfile
from PyCmd import deinit, init, parse_line, run_command
from unittest import TestCase, TestSuite, defaultTestLoader

class TestERRORLEVEL(TestCase):
    """Test if the ERRORLEVEL is as expected."""
    def setUp(self):
        (handle, tmpfile) = tempfile.mkstemp()
        os.close(handle)
        self.tmpfile_out = tmpfile

        (handle, tmpfile) = tempfile.mkstemp(suffix = '.bat')
        os.close(handle)
        self.tmpfile_bat = tmpfile

        init()

        # Execute a command that yields ERRORLEVEL 0 to try to
        # make this the current ERRORLEVEL as far as PyCmd is
        # concerned; might reduce side effects from previous
        # test cases:
        tokens = parse_line('dir >nul')
        run_command(tokens)

    def tearDown(self):
        tmpfile = self.tmpfile_out
        try:
            os.remove(tmpfile)
        except:
            self.fail('Removing temporary file failed: ' + tmpfile)

        tmpfile = self.tmpfile_bat
        try:
            os.remove(tmpfile)
        except:
            self.fail('Removing temporary file failed: ' + tmpfile)

        deinit()

    def testERRORLEVELInteractive(self):
        """Check ERRORLEVEL when accessing it directly, like in 'echo %ERRORLEVEL%'.

        This test is based on knowing that the implementation for
        maintaining the ERRORLEVEL may differentiate between
        directly accessing ERRORLEVEL in the command to be executed
        vs. having it accessed by a batch file.
        """
        tmpfile = self.tmpfile_out

        # "dir nul" should result in ERRORLEVEL 1
        tokens = parse_line('dir nul >nul 2>&1')
        run_command(tokens)

        # Capture ERRORLEVEL in tmpfile
        tokens = parse_line('echo %ERRORLEVEL% >"' + tmpfile + '"')
        run_command(tokens)
        f = open(tmpfile, 'r')
        s = f.read()
        f.close()
        self.assertEquals('1', s[0])

    def testERRORLEVELInteractiveMultiple(self):
        """Check ERRORLEVEL when accessing it directly with multiple commands, like in 'dir nul & echo %ERRORLEVEL%'.

        This tests whether the cmd.exe behavior of replacing all
        occurrences of "%ERRORLEVEL%" before executing any of the
        commands is mimicked.
        """

        # Execute a command that yields ERRORLEVEL 1 (we
        # do not want to use the cmd.exe default of ERRORLEVEL
        # 1)
        tokens = parse_line('dir nul >nul')
        run_command(tokens)

        # "dir" should yield ERRORLEVEL 0, but %ERRORLEVEL%
        # should be replaced first, so it should yield "1"
        tokens = parse_line('dir >nul 2>&1 & echo %ERRORLEVEL% >"' + self.tmpfile_out + '"')
        run_command(tokens)

        # Read ERRORLEVEL from tmpfile
        f = open(self.tmpfile_out, 'r')
        s = f.read()
        f.close()
        self.assertEquals('1', s[0])

    def testERRORLEVELNonInteractive(self):
        """Check ERRORLEVEL when accessing it indirectly, like in a batch file 'mybatch.bat'.

        This test is based on knowing that the implementation for
        maintaining the ERRORLEVEL may differentiate between
        directly accessing ERRORLEVEL in the command to be executed
        vs. having it accessed by a batch file.
        """

        # "dir nul" should yield ERRORLEVEL 1
        tokens = parse_line('dir nul >nul 2>&1')
        run_command(tokens)

        # Write batch file to capture ERRORLEVEL in tmpfile
        f = open(self.tmpfile_bat, 'w')
        f.writelines('echo %ERRORLEVEL% >"' + self.tmpfile_out + '"')
        f.close()

        # Execute batch file self.tmpfile_bat
        tokens = parse_line(self.tmpfile_bat)
        run_command(tokens)

        # Read ERRORLEVEL from self.tmpfile_out
        f = open(self.tmpfile_out, 'r')
        s = f.read()
        f.close()
        self.assertEquals('1', s[0])


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestERRORLEVEL))
    return suite

