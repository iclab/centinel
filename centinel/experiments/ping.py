import os

from centinel.experiment import Experiment

class PingExperiment(Experiment):
    name = "ping"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []

    def run(self):
        for line in self.input_file:
            self.host = line.strip()
            self.ping_test()

    def ping_test(self):
        result = {
            "host" : self.host,
        }

        print "Running ping to " + self.host      
        response = os.system("ping -c 1 " + self.host + " >/dev/null 2>&1")
        
        if response == 0:
            result["success"] = 'true'
        else:
            result["success"] = 'false'

        self.results.append(result)
