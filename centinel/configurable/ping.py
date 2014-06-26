import ConfigParser
import os

from centinel.experiment import Experiment

class ConfigurablePingExperiment(Experiment):
    name = "config_ping"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []
	self.args = dict()

    def run(self):
	parser = ConfigParser.ConfigParser()
	parser.read([self.input_file,])
	if not parser.has_section('Ping'):
	    return

	# currently unused, because ping
	# does not take many arguments.
	self.args.update(parser.items('Ping'))

	url_list = parser.items('URLS')
	for url in url_list[0][1].split():
	    self.host = url
            self.ping_test()

    def ping_test(self):
        result = {
            "host" : self.host,
        }

        print "Running ping to ", self.host      
        response = os.system("ping -c 1 " + self.host + " >/dev/null 2>&1")
        
        if response == 0:
            result["success"] = 'true'
        else:
            result["success"] = 'false'

        self.results.append(result)
