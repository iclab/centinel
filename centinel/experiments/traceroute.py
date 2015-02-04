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
            for m in self.methods:
                try:
                    logging.info("Running traceroute on" + 
                                 " %s using %s probes..." % (url, m.upper()))
                    result = traceroute.traceroute(url, method=m)
                    self.results.append(result)
                except Exception as e:
                    logging.warning("%s traceroute failed: %s" %
                                    (m.upper(), str(e)))
