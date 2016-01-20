from centinel.primitives.headless_browser import HeadlessBrowser
from centinel.experiment import Experiment

class HeadlessBrowserExperiment(Experiment):

    def __init__(self, input_file):
            self.input_file  = input_file
            self.results = []

    def run(self):
        hb = HeadlessBrowser()
        self.results = hb.run(input_file=self.input_file)
