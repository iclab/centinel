import unittest
import os.path
from test_output_format import bcolors
from ..primitives import traceroute

class TrancerouteUnitTest(unittest.TestCase):

    def setUp(self):
        self.error_list = {}
        cwd = os.getcwd()
        self.good_domains = []
        self.bad_domains = []
        with open(os.path.join(cwd,'centinel/data/traceroute.txt')) as testfile:
            domain = testfile.readline().rstrip('\n')
            while domain != '':
                self.good_domains.append(domain)
                domain = testfile.readline().rstrip('\n')
            testfile.close()
        print 'test start!'

    def test_traceroute(self):
        for domain in self.good_domains:
            result = traceroute.traceroute(domain)
            self._good_input_test(result)

        for domain in self.bad_domains:
            result = traceroute.traceroute(domain)
            self._bad_input_test(result)

    def _good_input_test(self, result):
        #GIVEN A VALID INPUT, RESULT SHOULD CONTAIN RETURN MESSAGE IN A HEALTHY FORMAT
        self._assert('assertFalse','error' in result, result)

    def _assert(self, assert_name, expr, result):
        try:
            self.__getattribute__(assert_name)(expr)
            print bcolors.OKGREEN + '%s passed' %(result['domain']) + bcolors.ENDC
        except AssertionError as err:
            err_msg = 'unknown error, no message given' if result['error'] is '' else result['error']
            self.error_list[result['domain']] = err_msg



    def _bad_input_test(self, result):
        #GIVEN A BAD INPUT, RESULT SHOULD CONTAIN ERROR MESSAGE
        #1. BAD DNS DOMAIN
        self.assertTrue('error' in result)
        self.assertIsNotNone(result['error'])
        #2. VALID DOMAIN BUT BAD RESPONES
        self.assertIsNotNone(result['unparseable_lines'])

    def tearDown(self):
        if self.error_list is not None:
            for err in self.error_list:
                print bcolors.FAIL + '%s %s' % (err, self.error_list[err]) + bcolors.ENDC
            raise AssertionError('%s errors found' % (len(self.error_list)))
        else:
            print 'ok all passed'


suite = unittest.defaultTestLoader.loadTestsFromTestCase(TrancerouteUnitTest)
unittest.TextTestRunner(verbosity=2).run(suite)

