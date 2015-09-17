import pytest
import re
from centinel.primitives import dnslib


class TestDnslib:

    @pytest.fixture(scope='module')
    def ipregex(self):
        return "^((((2(([0-4]\d)|(5[0-5]))\.)|(1\d\d\.))|([1-9]\d\.))|(\d\.)){3}((((2(([0-4]\d)|(5[0-5]))$)|(1\d\d$))|([1-9]\d$))|(\d$))"

    # 1. test good case response
    #   .1 test single domain w/ domain name
    def test_lookup_domain_good(self, ipregex, domain='www.google.com'):

        result = dnslib.lookup_domain(domain)

        #* test result is not None
        assert result is not None

        #* test query domain is matched given domain
        assert result['domain'] == domain, 'Requested domain name should match given domain name'

        #* test domainserver is not none
        assert result['nameserver'] is not None

        #* test first reqsposne is not none
        assert result['response1'] is not None

        #+ test the ip of first response
        assert result['response1-ips'] is not None

        #- test the ip is in a valid formula && matched known ip
        for ip in result['response1-ips']:
            assert re.match(ipregex, ip), 'ip is invalid'

        #* test second response is in the result ( whatever in it)
        assert 'response2' in result, 'second response should be in the result ( whatever is in it)'

        #+ test second response is not none
        if result['response2'] is not None:
            assert 'response2-ips' in result
            #- test the returned ip is in a valid formula && match known ip
            for ip in result['response2-ips']:
                assert re.match(ipregex, ip), 'ip is invalid'


    #   .2 test multiple domains w/ domain names
    def test_loopup_domains_good(self, ipregex):

        domains = ['www.google.com', 'www.github.com']
        results = dnslib.lookup_domains(domains)

        #* test results is not None
        assert results is not None

        #* test 'error' is not in result
        assert 'error' not in results

        #* test name of domains are in results
        for name in domains:
            assert name in results

    # 2. test handling of bad case
    #   .1 test single domain w/ domain name
    #     * test result is not none (even in bad case, the return value should exist)
    #+ no domain name given
    def test_lookup_domain_bad_domain_name(self):

        #+ invalid domain name
        domain = 'www.gosdafeefwqmqwnpqpjdvzgle.s.adf.wefpqwfm.ewqfqpwqrqwn.com'
        result = dnslib.lookup_domain(domain)

        #- test response1 is none
        assert result is not None
        assert 'response1' in result

        #- test response1 is none
        assert result['response1'] is not None
        assert result['response1-ips'] == []



    #+ valid domain name with invalid servername
    @pytest.mark.xfailed
    def test_lookup_domain_bad_servername(self):

        servername = []
        domain = 'www.google.com'

        with pytest.raises(RuntimeError):

            result = dnslib.lookup_domain(domain, servername)
            assert result is not None

            #- test response1 is none
            assert 'response1' in result
            assert result['response1'] is None

    #.2 test multiple domains
    @pytest.mark.skipif(True)
    def test_lookup_domains_thread_error(self):

        #* test results is not none
        #+ given a great number of domains
        domains = []
        result = dnslib.lookup_domains(domains)

        #- test 'error' is in results
        assert result is not None
        assert 'error' in result
        assert result['error'] is "Threads took too long to finish."


    # 3. others
    # .1 test send chaos queries
    def test_send_chaos_queries(self):

        result = dnslib.send_chaos_queries()

        assert result is not None

        #* test at least one nameserver in a name field of results is not none
        for name in result:
            isNone = True
            for nameserver in name:
                if nameserver is not None:
                    isNone = False
            assert not isNone


pytest.main('-v')
