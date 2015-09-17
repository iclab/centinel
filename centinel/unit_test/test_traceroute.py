import pytest
from centinel.primitives import traceroute


class TestTraceRoute:
    #1. test good case
    def test_traceroute_valid_domain(self):
        domain = 'www.google.com'
        result = traceroute.traceroute(domain)
        #.1 test traceroute results is not none
        assert result is not None
        #* test domain is matched with given domain
        assert result['domain'] == domain

        #* test method is not none
        assert result['method'] is not None
        #+ test method is udp if no method given
        assert result['method'] == 'udp'
        assert 'error' not in result

        #* test other field is not None
        assert result["domain"] is not None
        assert result["method"] is not None
        assert result["total_hops"] is not None
        assert result["meaningful_hops"] is not None
        assert result["hops"] is not None
        assert result["unparseable_lines"] is not None
        assert result["forcefully_terminated"] is not None
        assert result["time_elapsed"] is not None

    #+ test method is tcp if given method as tcp
    def test_traceroute_tcp_connection(self):
        domain = 'www.google.com'
        result = traceroute.traceroute(domain, 'tcp')
        assert result is not None
        #* test 'error' is not in the results
        assert 'error' not in result


    # 2. test bad case
    def test_traceroute_invalid_domain_name(self):
        #.1 given a invalid domain name
        domain = 'www.sdfadsfdasefwefewfew.fewfwefw.fwefwfsafdas.com'
        result = traceroute.traceroute(domain)
        #* test 'error' is not none
        assert result is not None
        assert 'error' in result
        #+ test 'error' is ': name or service not known'
        assert result['error'] == ': name or service not known'

    # .2 given a great number of domain names
    @pytest.mark.skipif(True)
    def test_traceroute_batch(self):
        domains = []
        result = traceroute.traceroute_batch(domains)
        assert result is not None
        #* test 'error' is in results
        assert 'error' in result
        #+ test 'error' is "Threads took too long to finish."
        assert result['error'] == "Threads took too long to finish."
