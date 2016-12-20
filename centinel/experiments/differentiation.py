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

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.external_results = {}
        self.configs = Configs()

        self.configs.set('pcap_folder', self.global_constants['data_dir'])

        if self.params is not None:
            for key in self.params:
                self.configs.set(key,self.params[key])

    def run(self):

        diff_result = replay_client.main()
        self.results.append(diff_result)

        jitter_folder = Configs().get('jitterFolder')
        result_files = [path for path in glob.glob(
                os.path.join(jitter_folder, '*.txt'))]
        for file in result_files:
           f = open(file)
           contents = f.read()
           name, ext = os.path.splitext(os.path.basename(file))
           self.external_results[name] = contents



