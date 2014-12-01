import os
import sys
import json
import glob
import imp
import logging
import random
import tarfile
import time

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
        """This function will return the list of experiments to run and manage
        our scheduling

        Note: this function will check the experiments directory for a
        special file, scheduler.info, that details how often each
        experiment should be run and the last time the experiment was
        run. If the time since the experiment was run is shorter than
        the scheduled interval in seconds, then the experiment will
        not be returned

        """

        sched_filename = os.path.join(self.config['dirs']['experiments_dir'],
                                      'scheduler.info')
        sched_info = {}
        if os.path.exists(sched_filename):
            with open(sched_filename, 'r') as file_p:
                sched_info = json.load(file_p)

        # look for experiments in experiments directory
        for path in glob.glob(os.path.join(self.config['dirs']['experiments_dir'],
                                           '[!_]*.py')):
            # get name of file and path
            name, ext = os.path.splitext(os.path.basename(path))
            # check if we should preempt on the experiment (if the
            # time to run next is greater than the current time) and
            # store the last run time as now
            #
            # Note: if the experiment is not in the scheduler, then it
            # will be run every time the client runs
            if (name in sched_info):
                run_next = sched_info[name]['last_run']
                run_next += sched_info[name]['frequency']
                if run_next > time.time():
                    continue
                sched_info[name]['last_run'] = time.time()

            # load the experiment
            imp.load_source(name, path)

        # write out the updated last run times
        with open(sched_filename, 'w') as file_p:
            json.dump(sched_info, file_p)

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
        experiments_subset = experiments.items()

        if self.config['experiments']['random_subsetting'] and \
               self.config['experiments']['random_subset_size'] < \
                   len(experiments.items()):
            experiments_subset = [
                experiments.items()[i] for i in sorted(
                    random.sample(xrange(len(experiments.items())),
                                  self.config['experiments']
                                             ['random_subset_size']))
            ]

        for name, Exp in experiments_subset:
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

        json.dump(results, result_file, encoding="ISO-8859-1")
        result_file.close()

        result_files = [path for path in glob.glob(
            os.path.join(self.config['dirs']['results_dir'],'*.json'))]

        if len(result_files) >= self.config['results']['files_per_archive']:
            logging.info("Compressing and archiving results.")

            files_archived = 0
            archive_count = 0
            tar_file = None

            for path in result_files:
                if files_archived % self.config['results']['files_per_archive'] == 0:
                    archive_count += 1
                    archive_filename = "results-%s_%d.tar.bz2" % (
                        datetime.now().isoformat(), archive_count)
                    archive_file_path = os.path.join(self.config['dirs']['results_dir'],
                        archive_filename)
                    logging.info("Creating new archive (%s)." % archive_file_path)
                    if tar_file:
                        tar_file.close()
                    tar_file = tarfile.open(archive_file_path, "w:bz2")

                tar_file.add(path,
                             arcname = os.path.basename(path))
                os.remove(path)
                files_archived += 1

            if tar_file:
                tar_file.close()

        logging.info("All experiments over. Check results.")
