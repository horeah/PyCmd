#
# Unit tests for Window.py
#

from unittest import TestCase, TestSuite, defaultTestLoader
from Window import Window
from completion import wildcard_to_regex
from console import get_buffer_size

class TestWindow(TestCase):
    """Test the Window class"""

    def setUp(self):
        self.window_small = Window(['a.txt', 'aa.txt', 'A a b.txt2'],
                                    wildcard_to_regex('*'),
                                    width=40,
                                    height=0)
        self.window_large = Window(['f%010d.dll' % i for i in range(20)],
                                    wildcard_to_regex('*.dl'),
                                    width=80,
                                    height=4)


    def testInitialSize(self):
        self.assertEquals(self.window_small.height, 3)
        self.assertEquals(self.window_small.width, 40)
        self.assertEquals(self.window_small.column_width, 39)
        self.assertEquals(self.window_small.num_columns, 1)
        self.assertEquals(self.window_small.num_lines, 3)

        self.assertEquals(self.window_large.height, 4)
        self.assertEquals(self.window_large.width, 80)
        self.assertEquals(self.window_large.column_width, 25)
        self.assertEquals(self.window_large.num_columns, 3)
        self.assertEquals(self.window_large.num_lines, 7)


    def testFilter(self):
        self.window_small.filter = 'a b'
        self.assertEquals(self.window_small.num_lines, 1)
        self.window_small.filter = 'xx'
        self.assertEquals(self.window_small.num_lines, 0)
        self.assertEquals(self.window_small.column_width, 39)

        self.window_large.filter = '1'
        self.assertEquals(len(self.window_large.entries), 11)
        self.assertEquals(self.window_large.column_width, 25)
        self.assertEquals(self.window_large.num_columns, 3)
        self.assertEquals(self.window_large.num_lines, 4)
        self.window_large.filter = '0 19'
        self.assertEquals(len(self.window_large.entries), 1)
        self.assertEquals(self.window_large.column_width, 79)
        self.assertEquals(self.window_large.num_columns, 1)
        self.assertEquals(self.window_large.num_lines, 1)


def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromTestCase(TestWindow))
    return suite

