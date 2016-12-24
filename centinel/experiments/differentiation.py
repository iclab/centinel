#
# differentiation.py: An experiment which runs through a list of parsed pcaps and replays the tr# affic with a replay server to detect traffic differentiation.
#
# Input file contains a list of pcaps to replay. This list should be a subset of parsed pcaps al# already present.

import logging
import os
import time
import glob

from centinel.experiment import Experiment
from centinel.primitives import replay_client
from centinel.primitives.replay_client import *

class DifferentiationExperiment(Experiment):
    name = "differentiation"
    input_files = []

    def __init__(self, input_files):
        self.input_files = input_files
        self.results = []
        self.external_results = {}
        self.configs = Configs()

        if self.params is not None:
            for key in self.params:
                self.configs.set(key,self.params[key])

    def run(self):
        pcaps = {}
        for input_file in self.input_files.items():
            file_name, file_contents = input_file
            pcaps[file_name] = file_contents

        self.configs.set('pcaps', pcaps)
        diff_result = replay_client.main()
        self.results.append(diff_result)


