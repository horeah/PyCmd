import unittest
from tests import common

def suite():
    suite = unittest.TestSuite()
    suite.addTest(common.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
