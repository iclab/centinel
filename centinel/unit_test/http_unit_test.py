import pytest
from  centinel.primitives import http
import os
import sys

class TestHTTPMethods:

    def test_url_not_exist(capsys):
        """
        test if _get_http_request(args...) returns failure
        for an invalid url.
        """
        file_name = "../data/invalid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), file_name), 'r')
        #sys.stdout.write("Hello World!\n")
        for line in fd:
            line = line.rstrip('\n')
            res = http._get_http_request(line)
            assert 'failure' in res['response'].keys()

        fd.close()

    def test_url_exist(self):
        """
        test if _get_http_request(args..) returns valid contents from a
        valid url.
        """
        file_name = "../data/valid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), file_name), 'r')
        for line in fd:
            line = line.rstrip('\n')
            res = http._get_http_request(line)
            assert 'failure' not in res['response'].keys()
        fd.close()

    def test_batch_url(self):
        """
        test _get_http_request(arg...) primitive when a list of domain
        name is passed to get_requests_batch(args...).
        """
        invalid_hosts_file_name = "../data/invalid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), invalid_hosts_file_name), 'r')
        lines = [line.rstrip('\n') for line in fd]
        results = http.get_requests_batch(lines)
        # assert failure for inValid Hosts
        for key, result in results.items():
            assert 'failure' in result['response'].keys()
        fd.close()

        valid_hosts_file_name = "../data/valid_hosts.txt"
        fd = open(os.path.join(os.getcwd(), valid_hosts_file_name), 'r')
        lines = [line.rstrip('\n') for line in fd]
        results = http.get_requests_batch(lines)
        # assert no failure for valid hosts
        for key,result in results.items():
            assert 'failure' not in result['response'].keys()
        fd.close()

