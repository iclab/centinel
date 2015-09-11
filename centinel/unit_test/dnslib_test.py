import unittest
from ..primitives import dnslib

class DNSUnitTest(unittest.TestCase):

    def setUp(self):
        self.dnsQuery = dnslib.DNSQuery()
        self.ipregex = '^((2([0-5]){2}\.)|(([1][0-9]\d\.)|(([1-9]\d\.)|(\d\.)))){3}(2([0-5]){2}$)|(([1][0-9]\d$)|(([1-9]\d$)|(\d$)))'


    def test_lookup_domain(self):

        #CASE 1:
        # GIVEN A VALID DOMAIN NAME,
        # THE CLINT SHOULD RECEIVE TWO RESPONSES FROM THE DNS SEVER
        result = self.dnsQuery.lookup_domain("www.google.com")
        self._lookup_domain_helper(result)


    def test_send_chaos_queries(self):
        names = ["HOSTNAME.BIND", "VERSION.BIND", "ID.SERVER"]
        results = self.dnsQuery.send_chaos_queries()
        self.assertIsNotNone(results)
        for name in names:
            self.assertTrue(name in results)
            for nameserver in self.dnsQuery.nameservers:
                self.assertTrue(nameserver in results[name])

    def test_lookup_domains(self):
        results = self.dnsQuery.lookup_domains()
        if 'error' not in results:
            for result in results:
                self._lookup_domain_helper(result)
        else:
            print(results['error'])


    def _lookup_domain_helper(self, result):

        self.assertEqual("www.google.com", result['domain'])
        self.assertIsNotNone(result['nameserver'])

        #FIRST RESPONSE
        self.assertIsNotNone(result['response1'])
        self.assertIsNotNone(result['response1-ips'])
        for ip in result['response1-ips']:
            self.assertRegexpMatches(ip, self.ipregex, "parse_out_ips failed to parse ip correctly")

        #SECOND RESPONSE
        self.assertTrue('response2' in result)
        if 'response2-ips' in result:
            for ip in result['response2-ips']:
                self.assertRegexpMatches(ip, self.ipregex, "parse_out_ips failed to parse ip correctly")



    def tearDown(self):
        self.dnsQuery = None


suite = unittest.defaultTestLoader.loadTestsFromTestCase(DNSUnitTest)
unittest.TextTestRunner(verbosity=2).run(suite)



