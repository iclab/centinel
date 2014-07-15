import ConfigParser
import os
import subprocess
from centinel.experiment_py import Experiment
from centinel.utils import logger

class ConfigurableTracerouteExperiment(Experiment):
    name = "config_traceroute"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.args = dict()
        logger.log("i", "Running Traceroute Test")
  
    
    def run(self):
        parser = ConfigParser.ConfigParser()
        parser.read([self.input_file])
        if not parser.has_section('Traceroute'):
            return
        self.args.update(parser.items('Traceroute'))
	url_list = parser.items('URLS')
	
	if 'max_hops' in self.args.keys():
	    self.max_hops = int(self.args['max_hops'])
	else:
            self.max_hops = 30

	if 'start_hop' in self.args.keys():
	    self.start_hop = int(self.args['start_hop'])
	else:
            self.start_hop = 1

	if 'timeout' in self.args.keys():
	    self.timeout = int(self.args['timeout'])
	else:
            self.timeout = 10

	for url in url_list[0][1].split():
	    self.host = url
            self.traceroute()

    def isIp(self, string):
        a = string.split('.')
        if len(a) != 4:
           return False
        for x in a:
            if not x.isdigit():
                return False
            i = int(x)
            if i < 0 or i > 255:
                return False
        return True
      
    def traceroute(self):
        results = {
            "host" : self.host,
	    "max_hops" : self.max_hops,
	    "start_hop" : self.start_hop,
        }
	try:
	    t = self.start_hop
    	    finalIp = "Placeholder"
    	    complete_traceroute = ""
	    logger.log("i", "Conducting traceroute on " + self.host)
    	    for t in range(self.start_hop, self.max_hops + 1):
        	process = ['ping', self.host, '-c 1', '-t ' + str(t), '-W ' + str(self.timeout)]
        	response = subprocess.Popen(process, stdout=subprocess.PIPE).communicate()[0]
        	if t == 1:
		    if response == "":
			raise Exception("Host not available")
            	    pingSendInfo = response.splitlines()[0]
            	    pingSendSplit = pingSendInfo.split()
            	    finalIp = pingSendSplit[2].translate(None, '()')
        	ping_info = response.splitlines()[1]
        	split_by_word = str.split(ping_info)
        	reverseDns = "Not Found"
        	ip = "Not Found";
        	for string in split_by_word:
            	    stripped = string.translate(None, '():')
            	    if self.isIp(stripped):
                	ip = stripped
            	    if not '=' in stripped and '.' in stripped and not self.isIp(stripped):
                	reverseDns = stripped
        	complete_traceroute += ip + ";" + reverseDns
        	if ip == "Not Found" and reverseDns != "Not Found":
            	    pass
        	if ip == finalIp or t == self.max_hops:
            	    logger.log("s", "Finished Traceroute")
            	    break
        	else:
            	    complete_traceroute += "->"
    	    results["Hops"] = t
    	    results["traceroute"] = complete_traceroute
	except Exception as e:
	    logger.log("e", "Error occured in traceroute for " + self.host + ": " + str(e))
	    results["error"] = str(e)
	self.results.append(results)
