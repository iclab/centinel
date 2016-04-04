from centinel.primitives.headless_browser import HeadlessBrowser
from centinel.experiment import Experiment


class HeadlessBrowserExperiment(Experiment):
    name = "headless_browser"

    def __init__(self, input_files):
            self.input_files = input_files
            self.results = []

    def run(self):
        hb = HeadlessBrowser()
        self.results = hb.run(input_files=self.input_files)
