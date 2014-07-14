import ConfigParser
import os
import subprocess

from centinel.experiment_py import Experiment

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


	self.args.update(parser.items('Ping'))
	
        if 'packets' in self.args.keys():
	    self.packets = int(self.args['packets'])
	else:
            self.packets = 1

	if 'timeout' in self.args.keys():
	    self.timeout = int(self.args['timeout'])
	else:
	    self.timeout = 10
            
	url_list = parser.items('URLS')
	for url in url_list[0][1].split():
	    self.host = url
            self.ping_test()

    def ping_test(self):
        result = {
            "host" : self.host,
        }
        print "Running ping to ", self.host      
        response = os.system("ping -c 1 -W " + str(self.timeout) + " " + self.host + " >/dev/null 2>&1")
        
        if response == 0:
            result["success"] = 'true'
            # Further experiment
            process = ['ping', self.host, '-c ' + str(self.packets), '-W ' + str(self.timeout)]
            console_response = subprocess.Popen(process, stdout=subprocess.PIPE).communicate()[0]
            ping_data = ""
            for line in console_response.splitlines():
                if "packets transmitted" in line and "received" in line:
                    ping_data = line
                    break
            split_data = ping_data.split()
            packetsTransmitted = -1
            packetsReceived = -1
            packetsLostPercentage = -1 #From 0 - 100
            for x in range(0, len(split_data) - 1):
                if split_data[x] == "packets" and split_data[x + 1].replace(",", "") == "transmitted":
                    packetsTransmitted = int(split_data[x - 1])
                    print("Packets Transmitted: " + str(packetsTransmitted))
                if split_data[x].replace(",", "") == "received":
                    packetsReceived = int(split_data[x - 1])
                    print("Packets Received: " + str(packetsReceived))
                if split_data[x].replace(",", "") == "loss" and  split_data[x - 1] == "packet":
                    packetsLostPercentage = int(split_data[x - 2].replace("%", ""))
                    print("Packets Lost %: " + str(packetsLostPercentage))
            result["sent"] = str(packetsTransmitted)
            result["received"] = str(packetsReceived)
            result["percent_lost"] = str(packetsLostPercentage)
        else:
            result["success"] = 'false'
        self.results.append(result)
