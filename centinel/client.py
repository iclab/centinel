import os
import sys
import json
import glob
import imp
import logging
import tarfile

from datetime import datetime

from experiment import Experiment, ExperimentList


class Client():

    def __init__(self, config):
        self.config = config

    def setup_logging(self):
        logging.basicConfig(filename=self.config['log']['log_file'],
                            format=self.config['log']['log_format'],
                            level=self.config['log']['log_level'])

    def get_result_file(self):
        result_file = "result-%s.json" % (datetime.now().isoformat())
        return os.path.join(self.config['dirs']['results_dir'], result_file)

    def get_input_file(self, experiment_name):
        input_file = "%s.txt" % (experiment_name)
        return os.path.join(self.config['dirs']['data_dir'], input_file)

    def load_experiments(self):
        # look for experiments in experiments directory
        for path in glob.glob(os.path.join(self.config['dirs']['experiments_dir'],
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
            self.config['dirs']['results_dir'] = os.path.join(centinel_home,
                                                              'results')

        logging.info('Started centinel')

        if not os.path.exists(self.config['dirs']['results_dir']):
            logging.warn("Creating results directory in "
                         "%s" % (self.config['dirs']['results_dir']))
            os.makedirs(self.config['dirs']['results_dir'])

        result_file_path = self.get_result_file()
        result_file = open(result_file_path, "w")
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

        logging.info("Compressing and archiving results.")
        archive_filename = "results-%s.tar.bz2" % datetime.now().strftime("%m-%d-%Y")
        archive_file_path = os.path.join(self.config['dirs']['results_dir'], archive_filename)
        temp_dir = os.path.join(self.config['dirs']['results_dir'], "tmp-%s" % datetime.now().isoformat())

        if os.path.isfile(archive_file_path):
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            with tarfile.open(archive_file_path, "r:bz2") as tar:
                tar.extractall(temp_dir)
            with tarfile.open(archive_file_path, "w:bz2") as tar:
                tar.add(result_file_path, arcname = os.path.basename(result_file_path))
                for filename in glob.glob(os.path.join(temp_dir, "*.json")):
                    tar.add(filename, arcname = os.path.basename(filename))
                    os.remove(filename)
            os.remove(result_file_path)
            os.rmdir(temp_dir)
        else:
            logging.info("Creating new archive for today (%s)." % archive_file_path)
            with tarfile.open(archive_file_path, "w:bz2") as tar:
                tar.add(result_file_path, arcname = os.path.basename(result_file_path))
            os.remove(result_file_path)

        logging.info("All experiments over. Check results.")
