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

	url_list = parser.items('URLS')
	for url in url_list[0][1].split():
	    self.host = url
            self.dns_test()

    def dns_test(self):
	result = {
            "host" : self.host,
	    "resolver" : self.resolver
        }
	
	res = dns.resolver.query(self.host, 'A')
	ans = ""
	for i in res.response.answer:
	    if ans == "":
		ans = i.to_text()
	    else:
		ans = ans + ", " + i.to_text()

        result["A"] = ans

        self.results.append(result)
