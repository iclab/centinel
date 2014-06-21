# first allow imports from parent directory.
# not particularly elegant but it seems to work well.
import sys
#sys.path.append("..")
from ponyfunctions import PonyFunctions

import os
import socket

# needed in order to conform with Centinel format
from centinel.experiment import Experiment

from logging import log
import unittest


#class TestPonyFunctions(unittest.TestCase):
class TestPonyFunctions(Experiment):
    name="pony_ping"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []
	self.setUp()

    def run(self):
        for line in self.input_file:
            self.host = line.strip()
            self.test_ponyping()

    def setUp(self):
        pass

    def test_ponyping(self):
        """   def pony_ping(output, ip, port=80, packettype="icmp", mincount=1,
                  interval=0, retry=1, timeout=2, snifftimeout=0):
        """
	result = {
            "host" : self.host,
        }

        print "Running ping to " + self.host      
        response = os.system("ping -c 1 " + self.host + " >/dev/null 2>&1")
        
        if response == 0:
            result["success"] = 'true'
        else:
            result["success"] = 'false'

	try:
    	    a = PonyFunctions.pony_ping("", self.host)
            result["icmp"] = a['response']
	except socket.gaierror,e:
	    result["icmp"] = e[1]

        try:
	    a = PonyFunctions.pony_ping("", self.host, packettype="tcpsyn")
        
	    if(a['response'] is not None and a['response'] > 0):
        	result["tcpsyn_rtt"] = a['rtt'] > 0
		result["tcpsyn"] = a['response']
	except socket.gaierror,e:
	    result["tcpsyn"] = e[1]
        
	try:
	    a = PonyFunctions.pony_ping("", self.host, packettype="tcpack")
	    if(a['response'] is not None):
		result["tcpack"] = a['response']
	except socket.gaierror,e:
	    result["tcpack"] = e[1]

	try:
    	    a = PonyFunctions.pony_ping("", self.host, packettype="udp")
	    if(a['response'] is not None):
		result["udp"] = a['response']
	except socket.gaierror,e:
	    result["udp"] = e[1]

	self.results.append(result)

if __name__ == '__main__':
    unittest.main()
