from centinel.primitives.tcp_connect import tcp_connect
import logging

from centinel.experiment import Experiment

class TCPConnectExperiment(Experiment):
    name = "tcp_connect"

    def __init__(self, input_files):
        self.input_files = input_files
        self.results = []

    def run(self):
        for name, input_file in self.input_files.items():
            logging.info("Input file: " + name)
            for line in input_file:
                if line == "":
                    continue
                host, port = line.strip().split(' ')
                logging.debug("testing " + host + ":" + port + "...")
                self.results.append(tcp_connect(host, port))
