import pytest
import os
from  ..primitives import http

class TestHTTPMethods:

    def test_url_not_exist(self):
        """
        test if _get_http_request(args...) returns failure
        for an invalid url.
        """
        file_name = "data/invalid_hosts.txt"
        fd = open(file_name, 'r')
        for line in fd:
            line = line.rstrip('\n')
            res = http._get_http_request(line)
            assert res is not None
            assert 'failure' in res['response'].keys()

        fd.close()

    def test_url_exist(self):
        """
        test if _get_http_request(args..) returns valid contents from a
        valid url.
        """
        file_name = "data/valid_hosts.txt"
        fd = open(file_name, 'r')
        for line in fd:
            line = line.rstrip('\n')
            res = http._get_http_request(line)
            assert res is not None
            assert 'failure' not in res['response'].keys()
        fd.close()

    def test_batch_url_invalid_hosts(self):
        """
        test _get_http_request(arg...) primitive when a list of invaid domain
        name is passed to get_requests_batch(args...).
        """
        invalid_hosts_file_name = "data/invalid_hosts.txt"
        fd = open(invalid_hosts_file_name, 'r')
        lines = [line.rstrip('\n') for line in fd]
        results = http.get_requests_batch(lines)
        assert results is not None
        # assert failure for inValid Hosts
        for key, result in results.items():
            assert result is not None
            assert 'failure' in result['response'].keys()
        fd.close()


    def test_batch_url_valid_hosts(self):
        """
        test _get_http_request(arg...) primitive when a list of valid domain
        name is passed to get_requests_batch(args...).
        """
        valid_hosts_file_name = "data/valid_hosts.txt"
        fd = open(valid_hosts_file_name, 'r')
        lines = [line.rstrip('\n') for line in fd]
        results = http.get_requests_batch(lines)
        assert results is not None
        # assert no failure for valid hosts
        for key,result in results.items():
            assert result is not None
            assert 'failure' not in result['response'].keys()
        fd.close()

    def test_batch_url_thread_error(self):
        """
        test if thread takes long time to finish
        TODO: choose url that gives thread error
        """
        #file_name = "data/input_file.txt"
        #fd = open(file_name, 'r')
        #lines = [line.rstrip('\n') for line in fd]
        #result = http.get_requests_batch(lines)
        #assert result is not None
        #assert 'error' in result
        #assert result['error'] is "Threads took too long to finish."
        #fd.close()