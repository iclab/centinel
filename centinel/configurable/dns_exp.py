import dns.resolver
import ConfigParser
import os

from centinel.experiment_py import Experiment

class ConfigurableDNSExperiment(Experiment):
    name = "config_dns"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []
	self.args = dict()

    def run(self):
	parser = ConfigParser.ConfigParser()
	parser.read([self.input_file,])
	if not parser.has_section('DNS'):
	    return


	self.args.update(parser.items('DNS'))

	if 'resolver' in self.args.keys():
	    self.resolver = self.args['resolver']
	else:
            self.resolver = "8.8.8.8"

        if 'record' in self.args.keys():
            self.record = self.args['record']
        else:
            self.record = 'A'

        if 'timeout' in self.args.keys():
            self.timeout = int(self.args['timeout'])
        else:
            self.timeout = 3

	url_list = parser.items('URLS')
	for url in url_list[0][1].split():
	    self.host = url
            self.dns_test()

    def dns_test(self):
	result = {
            "host" : self.host,
	    "resolver" : self.resolver
        }
	ans = ""
	if self.record == 'A':
            res = dns.resolver.query(self.host, self.record)
            for i in res.response.answer:
                if ans == "":
                    ans = i.to_text()
                else:
                    ans = ans + ", " + i.to_text()
        else:
            try:
                query = dns.message.make_query(self.host, self.record)
                response = dns.query.udp(query, self.resolver, timeout=self.timeout)
                for answer in response.answer:
                    if ans == "":
                        ans = answer.to_text()
                    else:
                        ans += ", " + answer.to_text()
            except dns.exception.Timeout:
                print("Query Timed out for " + self.host)
                ans = "Timeout"
            except Exception:
                print("Error Querying " + self.record + " record for " + self.host)
                ans = "Error"
        if ans == "":
            ans = "Unavailable"
	print(ans)

        result["record_type"] = self.record
        result['record'] = ans
        

        self.results.append(result)
