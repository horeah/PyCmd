#
# Unit tests for console.py
#

from unittest import TestCase, TestSuite, defaultTestLoader
import console
from sys import stdout
from console import get_text_attributes, set_text_attributes
from pycmd_public import color

class TestColors(TestCase):
    """Test the manipulation of color attributes"""

    def setUp(self):
        self.orig_attr = get_text_attributes()
        
    def tearDown(self):
        set_text_attributes(self.orig_attr)

    def testRgbSet(self):
        """Test the setting of individual RGB components"""
        stdout.write(color.Fore.SET_RED +
                     color.Fore.SET_GREEN +
                     color.Fore.SET_BLUE +
                     color.Fore.SET_BRIGHT)
        attr = get_text_attributes()
        self.assertTrue(attr & console.FOREGROUND_RED 
                        and attr & console.FOREGROUND_GREEN 
                        and attr & console.FOREGROUND_BLUE
                        and attr & console.FOREGROUND_BRIGHT)

    def testRgbClear(self):
        """Test the clearing of individual RGB components"""
        stdout.write(color.Fore.CLEAR_RED +
                     color.Fore.CLEAR_GREEN +
                     color.Fore.CLEAR_BLUE +
                     color.Fore.CLEAR_BRIGHT)
        attr = get_text_attributes()
        self.assertFalse(attr & console.FOREGROUND_RED 
                         or attr & console.FOREGROUND_GREEN 
                         or attr & console.FOREGROUND_BLUE
                         or attr & console.FOREGROUND_BRIGHT)

    def testRgbToggle(self):
        """Test the toggling of individual RGB components"""
        attr = get_text_attributes()
        set_text_attributes(attr 
                            | console.FOREGROUND_RED 
                            | console.FOREGROUND_GREEN
                            | console.FOREGROUND_BLUE
                            | console.FOREGROUND_BRIGHT)
        stdout.write(color.Fore.TOGGLE_RED +
                     color.Fore.TOGGLE_GREEN +
                     color.Fore.TOGGLE_BLUE +
                     color.Fore.TOGGLE_BRIGHT)
        attr = get_text_attributes()
        self.assertFalse(attr & console.FOREGROUND_RED 
                         or attr & console.FOREGROUND_GREEN 
                         or attr & console.FOREGROUND_BLUE
                         or attr & console.FOREGROUND_BRIGHT)

    def testNamedColors(self):
        """Test the predefined colors (named combinations of RGB components)"""
        stdout.write(color.Fore.RED)
        attr = get_text_attributes()
        self.assertTrue(attr & console.FOREGROUND_RED
                        and not attr & console.FOREGROUND_GREEN
                        and not attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.GREEN)
        attr = get_text_attributes()
        self.assertTrue(not attr & console.FOREGROUND_RED
                        and attr & console.FOREGROUND_GREEN
                        and not attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.YELLOW)
        attr = get_text_attributes()
        self.assertTrue(attr & console.FOREGROUND_RED
                        and attr & console.FOREGROUND_GREEN
                        and not attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.BLUE)
        attr = get_text_attributes()
        self.assertTrue(not attr & console.FOREGROUND_RED
                        and not attr & console.FOREGROUND_GREEN
                        and attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.MAGENTA)
        attr = get_text_attributes()
        self.assertTrue(attr & console.FOREGROUND_RED
                        and not attr & console.FOREGROUND_GREEN
                        and attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.CYAN)
        attr = get_text_attributes()
        self.assertTrue(not attr & console.FOREGROUND_RED
                        and attr & console.FOREGROUND_GREEN
                        and attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.WHITE)
        attr = get_text_attributes()
        self.assertTrue(attr & console.FOREGROUND_RED
                        and attr & console.FOREGROUND_GREEN
                        and attr & console.FOREGROUND_BLUE)

        stdout.write(color.Fore.DEFAULT)
        attr = get_text_attributes()
        self.assertEqual(attr , self.orig_attr)


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestColors))
    return suite

