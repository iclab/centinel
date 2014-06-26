import centinel.utils.http as http

from centinel.experiment import Experiment

class HTTPRequestExperiment(Experiment):
    name = "http_request"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []
        self.host = None
        self.path = "/"

    def run(self):
        for line in self.input_file:
            self.host = line.strip()
            self.http_request()

    def http_request(self):
        result = http.get_request(self.host, self.path)
        self.results.append(result)
