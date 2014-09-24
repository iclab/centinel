import logging

from centinel.experiment import Experiment
from centinel.utils import tls

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
            self.fprs = []
            for entry in line[2:]:
                self.fprs.append(entry.strip().lower())
            self.tls_test()

    def tls_test(self):
        result = {"host": self.host}

        logging.info("Getting TLS Certificate from %s on port %s " % 
                     (self.host, self.port))
        fpr, cert = tls.get_fingerprint(self.host, self.port)
        result['fpr'] = fpr
        result['cert'] = cert
        if fpr in self.fprs:
            result["success"] = 'true'
        else:
            result["success"] = 'false'

        self.results.append(result)
