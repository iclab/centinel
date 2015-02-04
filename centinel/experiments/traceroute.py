import logging
import centinel.primitives.traceroute as traceroute


from centinel.experiment import Experiment


class TracerouteExperiment(Experiment):
    name = "traceroute"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []
        self.methods = ["icmp", "udp", "tcp"]

    def run(self):
        for line in self.input_file:
            url = line.strip()
            result = {}
            for method in self.methods:
                try:
                    logging.info("Running traceroute on" + 
                                 " %s using %s probes..."
                                 % (url, method.upper()))
                    result = traceroute.traceroute(url, method=method)
                    self.results.append(result)
                except Exception as exp:
                    logging.warning("%s traceroute failed: %s" %
                                    (method.upper(), str(exp)))
