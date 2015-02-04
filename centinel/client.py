import bz2
import glob
import imp
import json
import logging
import os
import random
import sys
import tarfile
import time

from datetime import datetime

from experiment import Experiment, ExperimentList

from centinel.primitives.tcpdump import Tcpdump

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

            logging.info("Running %s test." % (name))

            # if the experiment specifies a list of input file names,
            # load them.
            if Exp.input_files is not None:
                input_files = {}
                for filename in Exp.input_files:
                    file_handle = self.load_input_file(filename)
                    if file_handle is not None:
                        input_files[filename] = file_handle
            else:
            # otherwise, fall back on [experiment name].txt
                input_files = self.load_input_file(name)
                if input_files is None:
                    continue

            try:
                root = True
                if os.geteuid() != 0:
                    logging.info("Centinel is not running as root, "
                                 "tcpdump will not start.")
                    root = False

                td = Tcpdump()
                tcpdump_started = False

                try:
                    if root and self.config['results']['record_pcaps']:
                        td.start()
                        tcpdump_started = True
                        logging.info("tcpdump started...")
                        # wait for tcpdump to initialize
                        time.sleep(2)
                except Exception as e:
                    logging.warning("Failed to run tcpdump: %s" %(e))

                # run the experiment
                exp = Exp(input_files)
                exp.run()

                if tcpdump_started:
                    logging.info("Waiting for tcpdump to process packets...")
                    # 5 seconds should be enough. this hasn't been tested on
                    # a RaspberryPi or a Hummingboard i2
                    time.sleep(5)
                    td.stop()
                    logging.info("tcpdump stopped.")
                    try:
                        pcap_file_name = "pcap_%s-%s.pcap.bz2" % (name, 
                            datetime.now().isoformat())

                        pcap_file_path = os.path.join(
                            self.config['dirs']['results_dir'], pcap_file_name)

                        with open(pcap_file_path, 'w:bz2') as file_p:
                            data = bz2.compress(td.pcap())
                            file_p.write(data)
                            logging.info("Saved pcap to %s."
                                         % (pcap_file_path))
                    except Exception as e:
                        logging.warning("Failed to write pcap file: %s" %(e))

            except Exception, e:
                logging.error("Error in %s: %s" % (name, str(e)))

            # close input file handle(s)
            if type(input_files) is dict:
                for file_name, file_handle in input_files.items():
                    file_handle.close()
            else:
                input_files.close()

            results[name] = exp.results

        json.dump(results, result_file)
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

    def load_input_file(self, name):
        input_file = self.get_input_file(name)

        if not os.path.isfile(input_file):
            logging.warn("Input file not found %s" % (input_file))
            return None

        try:
            input_file_handle = open(input_file)
        except Exception as e:
            logging.error("Can not read from %s" % (input_file))
            return None

        return input_file_handle
