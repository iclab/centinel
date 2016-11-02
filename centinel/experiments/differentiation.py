#
# differentiation.py: An experiment which runs through a list of parsed pcaps and replays the tr# affic with a replay server to detect traffic differentiation.
#
# Input file contains a list of pcaps to replay. This list should be a subset of parsed pcaps al# already present.


import logging
import os
import time
import glob

from centinel.experiment import Experiment
import replay_client


class DifferentiationExperiment(Experiment):
    name = "differentiation"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.external_results = {}

    def run(self):
       for filename, file in self.input_file.items():

            for pcapFolder in file.readlines():
                replay_client.initialSetup(pcapFolder)
                replay_client.run()
                jitter_folder = Configs().get('jitterFolder')
                result_files = [path for path in glob.glob(
                    os.path.join(jitter_folder, '*.txt'))]
                for file in result_files:
                    f = open(file)
                    contents = f.read()
                    name, ext = os.path.splitext(os.path.basename(file))
                    self.external_results[name] = contents



