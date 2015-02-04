import centinel.primitives.http as http

from centinel.experiment import Experiment


class MultiInputHTTPRequestExperiment(Experiment):
    """ This is the multiple-input-file HTTP
    experiment. You can specify filenames using the
    list in the class definition to have Centinel
    load them prior to running the experiment.
    """

    name = "multi_input_http_request"
    # filenames should not have extentions
    # (.txt is appended automatically)
    input_files = ['input_1', 'input_2']

    def __init__(self, input_files):
        # input handles passed using constructor
        # are stored in a dictionary with elements
        # like { '[filename]' : [file handle] }
        self.input_files = input_files
        self.results = []
        self.host = None
        self.path = "/"

    def run(self):
        for filename, input_file in self.input_files.items():
            for line in input_file:
                self.host = line.strip()
                self.http_request()

    def http_request(self):
        result = http.get_request(self.host, self.path)
        self.results.append(result)
