import unittest
from  centinel.primitives import http
import os


class TestHTTPMethods(unittest.TestCase):


    def test_URL_NotExist(self):
        """
        test if _get_http_request(args...) returns failure
        for an invalid url.
        """
        file_name = "centinel/unit_test/invalid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), file_name), 'r')
        for line in fd:
            line = line.rstrip('\n')
            res = http._get_http_request(line)
            self.assertIn('failure', res['response'].keys())
        fd.close()


    def test_URL_Exist(self):
        """
        test if _get_http_request(args..) returns valid contents from a
        valid url.
        """
        file_name = "centinel/unit_test/valid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), file_name), 'r')
        for line in fd:
            line = line.rstrip('\n')
            res = http._get_http_request(line)
            self.assertNotIn('failure', res['response'].keys())
        fd.close()

    def test_batch_URL(self):
        """
        test _get_http_request(arg...) primitive when a list of domain
        name is passed to get_requests_batch(args...).
        """
        invalid_hosts_file_name = "centinel/unit_test/invalid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), invalid_hosts_file_name), 'r')
        lines = [line.rstrip('\n') for line in fd]
        results = http.get_requests_batch(lines)
        # assert failure for inValid Hosts
        for key, result in results.items():
            self.assertIn('failure', result['response'].keys())
        fd.close()

        valid_hosts_file_name = "centinel/unit_test/valid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), valid_hosts_file_name), 'r')
        lines = [line.rstrip('\n') for line in fd]
        results = http.get_requests_batch(lines)
        # assert no failure for valid hosts
        for key,result in results.items():
            self.assertNotIn('failure', result['response'].keys())
        fd.close()


if __name__ == '__main__' :
    tests = unittest.TestLoader().loadTestsFromTestCase(TestHTTPMethods)
    unittest.TextTestRunner(verbosity=2).run(tests)