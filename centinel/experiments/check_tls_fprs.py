import logging

from centinel.experiment import Experiment
from centinel.primitives import tls


class TLSExperiment(Experiment):
    """Check the tls fingerprints of a site"""
    name = "tls"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []

    def run(self):
        for line in self.input_file:
            line = line.split(',')
            self.host, self.port = line[0].strip(), int(line[1].strip())
            self.fingerprints = [entry.strip().lower() for entry in line[2:]]
            self.tls_test()

    def tls_test(self):
        result = {"host": self.host}

        logging.info("Getting TLS Certificate from %s on port %s " %
                     (self.host, self.port))
        fingerprint, cert = tls.get_fingerprint(self.host, self.port)
        result['fingerprint'] = fingerprint
        result['cert'] = cert
        if fingerprint in self.fingerprints:
            result["success"] = 'true'
        else:
            result["success"] = 'false'

        self.results.append(result)
