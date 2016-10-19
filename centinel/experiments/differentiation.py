#
# differentiation.py: An experiment which runs through a list of parsed pcaps and replays the tr# affic with a replay server to detect traffic differentiation.
#
# Input file contains a list of pcaps to replay. This list should be a subset of parsed pcaps al# already present.


import logging
import os
import time

from centinel.experiment import Experiment
from centinel.primitives import replay_client


class DifferentiationExperiment(Experiment):
    name = "differentiation"

    def __init__(self, input_file):
        self.input_file = input_file

    def run(self):
       for line in self.input_file:
            self.pcapFolder = line.strip()
            replay_client.initialSetup(self.pcapFolder)
            replay_client.run()