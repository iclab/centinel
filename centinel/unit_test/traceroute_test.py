import unittest
from ..primitives import traceroute

class TrancerouteUnitTest(unittest.TestCase):

    def test_traceroute(self):
        result = traceroute.traceroute('stonybrook.edu')
        print result
        #GIVEN A VALID INPUT, RESULT SHOULD CONTAIN RETURN MESSAGE IN A HEALTHY FORMAT



        #GIVEN A BAD INPUT, RESULT SHOULD CONTAIN ERROR MESSAGE


suite = unittest.defaultTestLoader.loadTestsFromTestCase(TrancerouteUnitTest)
unittest.TextTestRunner(verbosity=2).run(suite)