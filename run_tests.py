import unittest
from tests import common_tests, completion_tests, pycmd_tests

def suite():
    suite = unittest.TestSuite()
    suite.addTest(common_tests.suite())
    suite.addTest(completion_tests.suite())
    suite.addTest(pycmd_tests.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
