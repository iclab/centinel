from centinel.experiment_py import Experiment
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

        print "Getting TLS Certificate from {0} on port {1} ".format(self.host,
                                                                     self.port)
        fpr = tls.get_fingerprint(self.host, self.port)
        result['fpr'] = fpr
        if fpr in self.fprs:
            result["success"] = 'true'
        else:
            result["success"] = 'false'

        self.results.append(result)
