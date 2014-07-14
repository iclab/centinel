import ConfigParser
import os
import centinel.utils.http as http
import base64

from centinel.experiment_py import Experiment

class ConfigurableHTTPRequestExperiment(Experiment):
    name = "config_http"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []
        self.host = None
        self.path = "/"
	self.args = dict()
    def run(self):
	parser = ConfigParser.ConfigParser()
	parser.read([self.input_file,])
	if not parser.has_section('HTTP'):
	    return

	# currently unused, because http.get_request() 
	# does not take an awful lot of arguments.
	self.args.update(parser.items('HTTP'))


	url_list = parser.items('URLS')
	for url in url_list[0][1].split():
	    self.host = url
	    self.http_request()

    def http_request(self):
        # result = base64.b64encode(http.get_request(self.host, self.path))
	result = http.get_request(self.host, self.path)

	result["response"]["body"] = base64.b64encode(result["response"]["body"])
	print(result)
        self.results.append(result)
