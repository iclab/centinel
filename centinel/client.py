import os
import sys
import json
import glob
import imp
import logging

from datetime import datetime

from experiment import Experiment, ExperimentList


class Client():

    def __init__(self, config):
        self.config = config

    def setup_logging(self):
        logging.basicConfig(filename=self.config.log_file,
                            format=self.config.log_format,
                            level=self.config.log_level)

    def get_result_file(self):
        result_file = "result-%s.json" % (datetime.now().isoformat())
        return os.path.join(self.config.results_dir, result_file)

    def get_input_file(self, experiment_name):
        input_file = "%s.txt" % (experiment_name)
        return os.path.join(self.config.data_dir, input_file)

    def load_experiments(self):
        # look for experiments in experiments directory
        for path in glob.glob(os.path.join(self.config.experiments_dir,
                                           '[!_]*.py')):
            # get name of file and path
            name, ext = os.path.splitext(os.path.basename(path))
            # load the experiment
            imp.load_source(name, path)

        # return dict of experiment names and classes
        return ExperimentList.experiments

    def run(self, data_dir=None):
        # XXX: android build needs this. refactor
        if data_dir:
            centinel_home = data_dir
            self.config.results_dir = os.path.join(centinel_home, 'results')

        logging.info('Started centinel')

        if not os.path.exists(self.config.results_dir):
            logging.warn("Creating results directory in "
                         "%s" % (self.config.results_dir))
            os.makedirs(self.config.results_dir)

        result_file = self.get_result_file()
        result_file = open(result_file, "w")
        results = {}

        experiments = self.load_experiments()

        for name, Exp in experiments.items():
            input_file = self.get_input_file(name)

            if not os.path.isfile(input_file):
                logging.warn("No input file found for %s. Skipping test."
                             "" % (name))
                continue

            logging.info("Reading input from %s" % (input_file))
            input_file = open(input_file)

            try:
                logging.info("Running %s test." % (name))
                exp = Exp(input_file)
                exp.run()
            except Exception, e:
                logging.error("Error in %s: %s" % (name, str(e)))

            input_file.close()

            results[name] = exp.results

        json.dump(results, result_file)
        result_file.close()

        logging.info("All experiments over. Check results.")
