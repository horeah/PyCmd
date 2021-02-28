import unittest
from tests import common_tests, completion_tests, console_tests, InputState_tests, Window_tests

def suite():
    suite = unittest.TestSuite()
    suite.addTest(common_tests.suite())
    suite.addTest(completion_tests.suite())
    suite.addTest(console_tests.suite())
    suite.addTest(InputState_tests.suite())
    suite.addTest(Window_tests.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
