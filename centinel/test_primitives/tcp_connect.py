import ConfigParser
import socket

from centinel.experiment import Experiment

class ConfigurableTCPConnectExperiment(Experiment):
    name = "conig_tcp_connect"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.host = None
        self.port = None
	self.args = dict()

    def run(self):
	parser = ConfigParser.ConfigParser()
	parser.read([self.input_file,])
	if not parser.has_section('TCP'):
	    return

	self.args.update(parser.items('TCP'))
	
	# one port for all of the URLs
 	if 'packets' in self.args.keys():
	    self.port = self.args['port']
	else:
            self.port = "80"

	url_list = parser.items('URLS')
	for url in url_list[0][1].split():
	    self.host = url
            self.tcp_connect()

    def tcp_connect(self):
        result = {
            "host" : self.host,
            "port" : self.port
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, int(self.port)))
            sock.close()
            result["success"] = "true"
        except Exception as err:
            result["failure"] = str(err)

        self.results.append(result)
