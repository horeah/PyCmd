#
# Unit tests for common.py
#

from unittest import TestCase, TestSuite, defaultTestLoader
from common import parse_line, unescape, fuzzy_match
from common import associated_application, full_executable_path, is_gui_application

class TestParseLine(TestCase):

    lines_to_parse = [

        ('dir >c:\\dir.txt',
         ['dir', '>', 'c:\\dir.txt']),

        ('dir >> c:\\dir.txt',
         ['dir', '>>', 'c:\\dir.txt']),

        ('sort <c:\\dir.txt',
         ['sort', '<', 'c:\\dir.txt']),

        ('dir 2>c:\\error.txt',
         ['dir', '2>', 'c:\\error.txt']),

#       This fails 
#        ('dir2>c:\\error.txt',
#         ['dir2', '>', 'c:\\error.txt']),

        ('2>&1 dir',
         ['2>&1', 'dir']),

        ('sort <c:\\dir.txt >c:\\sortdir.txt 2>c:\\error.txt',
         ['sort', '<', 'c:\\dir.txt', '>', 'c:\\sortdir.txt', '2>', 'c:\\error.txt']),

        ('dir >c:\\dir.txt 2>&1',
         ['dir', '>', 'c:\\dir.txt', '2>&1']),

        ('dir >&2 >>&2 1>&2 1>>&2 <&3 0<&3',
         ['dir', '>&2', '>>&2', '1>&2', '1>>&2', '<&3', '0<&3']),

        ('dir | sort',
         ['dir', '|', 'sort']),

        ('dir | sort | more',
         ['dir', '|', 'sort', '|', 'more']),

        ('cmd /c myscript.bat >result.txt',
         ['cmd', '/c', 'myscript.bat', '>', 'result.txt']),

        ('dir c:\\bin >files.txt & dir c:\\dos >>files.txt & type files.txt',
         ['dir', 'c:\\bin', '>', 'files.txt', '&', 'dir', 'c:\\dos', '>>', 'files.txt', '&', 'type', 'files.txt']),

        ('verify on || echo Verify command failed!!',
         ['verify', 'on', '||', 'echo', 'Verify', 'command', 'failed!!']),

        ('dir && copy a b && echo OK!',
         ['dir', '&&', 'copy', 'a', 'b', '&&', 'echo', 'OK!']),

        ('dir *.exe >files.txt & dir *.com >>files.txt',
         ['dir', '*.exe', '>', 'files.txt', '&', 'dir', '*.com', '>>', 'files.txt']),

        ('(dir *.exe & dir *.com) >files.txt',
         ['(dir', '*.exe', '&', 'dir', '*.com)', '>', 'files.txt']),

        ('((echo command1) & (echo command2)) && (echo command 3)',
         ['((echo', 'command1)', '&', '(echo', 'command2))', '&&', '(echo', 'command', '3)']),

        ('echo ^<dir^>',
         ['echo', '^<dir^>']),

        ('set varname="new&name"',
         ['set', 'varname="new&name"']),

        ('set varname=new^&name',
         ['set', 'varname=new^&name']),

        ('echo ""dd"dd" | grep dd',
         ['echo', '""dd"dd"', '|', 'grep', 'dd']),

        ('echo ""dd"dd"" | grep dd',
         ['echo', '""dd"dd"" | grep dd']),

        ('netstat -n -o | grep 127.0.0.1:80',
         ['netstat', '-n', '-o', '|', 'grep', '127.0.0.1:80']),

        ('httpd.exe /?',
         ['httpd.exe', '/?']),

        ('junction python ..\\..\\..\\python26',
         ['junction', 'python', '..\\..\\..\\python26']),

        ('grep -e "sed" *',
         ['grep', '-e', '"sed"', '*']),

        ('echo & echo',
         ['echo', '&', 'echo']),

        ('ant clean & ant',
         ['ant', 'clean', '&', 'ant']),

        ('echo && echo',
         ['echo', '&&', 'echo']),

        ('echo "Test_1|43&0&-100" | cut "-d&" -f 2',
         ['echo', '"Test_1|43&0&-100"', '|', 'cut', '"-d&"', '-f', '2']),

        ('openssl genrsa 1024 | openssl pkcs8 -topk8 -nocrypt -out test.key',
         ['openssl', 'genrsa', '1024', '|', 'openssl', 'pkcs8', '-topk8', '-nocrypt', '-out', 'test.key']),

        ('"c:\\Program Files\\MPlayer-1.0rc2\\mplayer.exe" dvd://0',
         ['"c:\\Program Files\\MPlayer-1.0rc2\\mplayer.exe"', 'dvd://0']),

        ('mplayer -sub "Night-On-Earth (1991).srt" -subdelay 5 "Night On Earth (1991).avi"',
         ['mplayer', '-sub', '"Night-On-Earth (1991).srt"', '-subdelay', '5', '"Night On Earth (1991).avi"']),

        ('java -cp d:\\docbook\\fop.jar;d:\\docbook\\serializer.jar;d:\\docbook\\commons-logging.jar;d:\\docbook\\commons-io.jar org.apache.fop.fonts.apps.TTFReader c:\\WINDOWS\\Fonts\\georgia.ttf fonts/georgia.xml',
         ['java', '-cp', 'd:\\docbook\\fop.jar;d:\\docbook\\serializer.jar;d:\\docbook\\commons-logging.jar;d:\\docbook\\commons-io.jar', 'org.apache.fop.fonts.apps.TTFReader', 'c:\\WINDOWS\\Fonts\\georgia.ttf', 'fonts/georgia.xml']),

        ('mkdir x&y',
         ['mkdir', 'x', '&', 'y']),

        ('mkdir "x&y"',
         ['mkdir', '"x&y"']),

        ('mkdir x^&y',
         ['mkdir', 'x^&y']),

        ('cd "x&y"\\',
         ['cd', '"x&y"\\']),

        ('cat "c:\\Documents and Settings\\user\\Local Settings\\Temp\\~DFF6E0.tmp"',
         ['cat', '"c:\\Documents and Settings\\user\\Local Settings\\Temp\\~DFF6E0.tmp"']),

        ('echo "1&2&3" | cut "-d&" -f3 >NUL 2>NUL',
         ['echo', '"1&2&3"', '|', 'cut', '"-d&"', '-f3', '>', 'NUL', '2>', 'NUL']),

        ('echo "1&2&3" | cut -d^& -f3 >NUL 2>NUL',
         ['echo', '"1&2&3"', '|', 'cut', '-d^&', '-f3', '>', 'NUL', '2>', 'NUL']),

        ('git push ssh://user@pycmd.git.sourceforge.net/gitroot/pycmd master',
         ['git', 'push', 'ssh://user@pycmd.git.sourceforge.net/gitroot/pycmd', 'master']),

        ('dir "c:\\Documents and Settings"\\',
         ['dir', '"c:\\Documents and Settings"\\']),

        ('dir "c:\\Documents and Settings\\"user"\\My Documents"',
         ['dir', '"c:\\Documents and Settings\\"user"\\My Documents"']),

        ('echo %RAILS_GEM_VERSION%',
         ['echo', '%RAILS_GEM_VERSION%']),

        ('cat ~\PUTTY.RND',
         ['cat', '~\PUTTY.RND']),

        ('CmBoxPgm.exe /QN1:F /F10 /P0 /CD /P0 /CD',
         ['CmBoxPgm.exe', '/QN1:F', '/F10', '/P0', '/CD', '/P0', '/CD']),

        ('FOR /R %I IN (.) DO IF "%~nI" equ "(2000) - Singles" ren "%~fI" "(0000) - Singles"',
         ['FOR', '/R', '%I', 'IN', '(.)', 'DO', 'IF', '"%~nI"', 'equ', '"(2000) - Singles"', 'ren', '"%~fI"', '"(0000) - Singles"']),

        ]

    strings_to_unescape = [
        ('Program^ Files', 'Program Files'),
        ('Program"^ "Files', 'Program"^ "Files'),
        ('Program^" Files^"', 'Program" Files"'),
        ('Documents^ and^ Settings', 'Documents and Settings'),
        ('HEAD^^', 'HEAD^'),
        ('x^ ^ y', 'x  y'),
        ('x^^y', 'x^y'),
        ('x^^^y', 'x^y'),
        ('x^^^^y', 'x^^y'),
        ('^\\^"\\^ ^ ^&&', '\\"\\  &&'),
        ('"^"', '"^"'),
        ('"^^"', '"^^"'),
        ('^"^"', '""'),
        ('^"ab^"', '"ab"'),
        ('^"ab"', '"ab"'),
        ('a"b"c', 'a"b"c'),
        ('a"^b"c', 'a"^b"c'),
        ('a"b^"c', 'a"b^"c'),
        ]

    def testParseLine(self):
        """Test that result of parse_line equals expected result."""
        for input, expected in self.lines_to_parse:
            self.assertEqual(parse_line(input), expected)

    def testReparseLine(self):
        """Test that reparse of print of first parse is unchanged."""
        for input, expected in self.lines_to_parse:
            first_parse = parse_line(input)
            second_parse = parse_line(' '.join(first_parse))
            self.assertEqual(first_parse, second_parse)

    def testUnescape(self):
        """Test that result of unescape equals expected result."""
        for input, expected in self.strings_to_unescape:
            self.assertEqual(unescape(input), expected)

class TestFuzzyMatch(TestCase):
    match_tests = [
        ('first', 'this first line will match first', [(5, 10)]),
        ('first', 'this line will not match', []),
        ('second line', 'this second line will match', [(5, 11), (12, 16)]),
        ('second line', 'this line will not match', []),
        ('third fourth', 'this fuzzily matches third and fourth', [(21, 26), (31, 37)]),
        ('third fourth', 'reversed fourth and third won\'t match', []),
        ('cd py', 'cd ~/pycmd', [(0, 2), (5, 7)])
    ]

    def testFuzzyMatch(self):
        for (substr, str, result) in self.match_tests:
            self.assertEqual(fuzzy_match(substr, str), result)

class TestAppIdentification(TestCase):
    """
    Test various functions used for identifying the executable
    that will be run for a given command, and its type (GUI or console)
    
    We rely on a few applications and file associations that are
    more-or-less standard in Windows; if things break here, make
    sure to check that the environment matches our assumptions.
    """
    standard_associations = { '.reg': 'regedit.exe',
                              '.chm': 'C:\\Windows\\hh.exe',}

    standard_app_locations = { 'cmdxxxxxx': None,
                      'c:\\windows\\system32\\___cxxxxxx___.exe': None,
                      'cmd': 'c:\\windows\\system32\\cmd.exe',
                      'cmd.exe': 'c:\\windows\\system32\\cmd.exe',
                      'c:\\windows\system32\\cmd': 'c:\\windows\\system32\\cmd.exe',
                      'c:\\windows\system32\\cmd.exe': 'c:\\windows\\system32\\cmd.exe',
                      'winhlp32': 'c:\\windows\\winhlp32.exe',
                      'winhlp32.exe': 'c:\\windows\\winhlp32.exe',
                      'c:\\windows\\winhlp32': 'c:\\windows\\winhlp32.exe',
                      'c:\\windows\\winhlp32.exe': 'c:\\windows\\winhlp32.exe',}

    standard_app_types = {'c:\\windows\\notepad.exe': True, 
                          'c:\\windows\\system32\\cmd.exe': False, }
                      
    def testAssociatedApplication(self):
        """
        Test the (registry-based) detection of the app associated to
        an extension
        """
        for ext, app in self.standard_associations.items():
            self.assertEqual(associated_application(ext).strip('"').lower(), 
                             app.lower())

    def testFullExecutablePath(self):
        """
        Test the function that tries to find out the actual executable 
        that will be spawned for a command
        """
        for cmd, app in self.standard_app_locations.items():
            if app is None:
                self.assertEqual(full_executable_path(cmd), None)
            else:
                self.assertEqual(full_executable_path(cmd).lower(), app.lower())

    def testIsGuiApplication(self):
        """Test the detection of the app type (GUI vs. console)"""
        for app, type in self.standard_app_types.items():
            self.assertEqual(is_gui_application(app), type)


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestParseLine))
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestFuzzyMatch))
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestAppIdentification))
    return suite

