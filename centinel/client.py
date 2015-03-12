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

    def get_result_file(self, name, start_time):
        result_file = "%s-%s.json.bz2" % (name, start_time)
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
            try:
                imp.load_source(name, path)
            except Exception as exception:
                logging.error("Failed to load experiment %s: %s" % (name, exception))

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

        logging.info('Centinel started.')

        if not os.path.exists(self.config['dirs']['results_dir']):
            logging.warn("Creating results directory in "
                         "%s" % (self.config['dirs']['results_dir']))
            os.makedirs(self.config['dirs']['results_dir'])

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

            logging.info("Running %s..." % (name))
            exp_start_time = datetime.now().isoformat()

            results = {}

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
                # instantiate the experiment
                exp = Exp(input_files)
            except Exception as exception:
                logging.error("Error initializing %s: %s" % (name, exception))
                results["init_exception"] = str(exception)

            run_tcpdump = True

            if self.config['results']['record_pcaps'] is False:
                logging.info("Your configuration has disabled pcap "
                             "recording, tcpdump will not start.")
                run_tcpdump = False
                # disable this on the experiment too
                exp.record_pcaps = False

            if run_tcpdump and os.geteuid() != 0:
                logging.info("Centinel is not running as root, "
                                 "tcpdump will not start.")
                run_tcpdump = False

            if run_tcpdump and Exp.overrides_tcpdump:
                logging.info("Experiment overrides tcpdump recording.")
                run_tcpdump = False

            td = Tcpdump()
            tcpdump_started = False

            try:
                if run_tcpdump:
                    td.start()
                    tcpdump_started = True
                    logging.info("tcpdump started...")
                    # wait for tcpdump to initialize
                    time.sleep(2)
            except Exception as e:
                logging.warning("Failed to run tcpdump: %s" %(e))

            try:
                # run the experiment
                exp.run()
            except Exception as exception:
                logging.error("Error running %s: %s" % (name, exception))
                results["runtime_exception"] = str(exception)

            # save any external results that the experiment has generated
            # they could be anything that doesn't belong in the json file
            # (e.g. pcap files)
            # these should all be compress with bzip2
            # the experiment is responsible for giving these a name and
            # keeping a list of files in the json results
            results_dir = self.config['dirs']['results_dir']
            if exp.external_results is not None:
                for fname, fcontents in exp.external_results.items():
                    external_file_name = ("external_%s-%s-%s"
                                          ".bz2" % (name,
                                                    exp_start_time,
                                                    fname))
                    external_file_path = os.path.join(results_dir,
                                                      external_file_name)
                    try:
                        with open(external_file_path, 'w:bz2') as file_p:
                            data = bz2.compress(fcontents)
                            file_p.write(data)
                    except Exception as exp:
                        logging.warning("Failed to write external file:"
                                        "%s" %(exp))

            if tcpdump_started:
                logging.info("Waiting for tcpdump to process packets...")
                # 5 seconds should be enough. this hasn't been tested on
                # a RaspberryPi or a Hummingboard i2
                time.sleep(5)
                td.stop()
                logging.info("tcpdump stopped.")
                try:
                    pcap_file_name = ("pcap_%s-%s.pcap"
                                      ".bz2" % (name, exp_start_time))
                    pcap_file_path = os.path.join(results_dir,
                                                  pcap_file_name)

                    with open(pcap_file_path, 'w:bz2') as file_p:
                        data = bz2.compress(td.pcap())
                        file_p.write(data)
                        logging.info("Saved pcap to "
                                     "%s." % (pcap_file_path))
                except Exception as exception:
                    logging.warning("Failed to write pcap file: %s" %(exception))


            # close input file handle(s)
            if type(input_files) is dict:
                for file_name, file_handle in input_files.items():
                    file_handle.close()
            else:
                input_files.close()

            try:
                results[name] = exp.results
            except Exception as exception:
                logging.error("Error saving results for "
                              "%s: %s" % (name, exception))
                results["results_exception"] = str(exception)

            # Pretty printing results will increase file size, but files are
            # compressed before sending.
            result_file_path = self.get_result_file(name, exp_start_time)
            result_file = bz2.BZ2File(result_file_path, "w")
            json.dump(results, result_file, indent = 2,
                      separators=(',', ': '))
            result_file.close()

        result_files = [path for path in glob.glob(
            os.path.join(self.config['dirs']['results_dir'],'*.json.bz2'))]

        if len(result_files) >= self.config['results']['files_per_archive']:
            logging.info("Compressing and archiving results.")

            files_archived = 0
            archive_count = 0
            tar_file = None
            files_per_archive = self.config['results']['files_per_archive']
            results_dir = self.config['dirs']['results_dir']
            for path in result_files:
                if files_archived % files_per_archive  == 0:
                    archive_count += 1
                    archive_filename = "results-%s_%d.tar.bz2" % (
                        datetime.now().isoformat(), archive_count)
                    archive_file_path = os.path.join(results_dir,
                                                     archive_filename)
                    logging.info("Creating new archive"
                                 " %s" % archive_file_path)
                    if tar_file:
                        tar_file.close()
                    tar_file = tarfile.open(archive_file_path, "w:bz2")

                tar_file.add(path,
                             arcname = os.path.basename(path))
                os.remove(path)
                files_archived += 1

            if tar_file:
                tar_file.close()

        logging.info("Finished running experiments. Look in %s for "
                     "results." % (self.config['dirs']['results_dir']))

    def load_input_file(self, name):
        input_file = self.get_input_file(name)

        if not os.path.isfile(input_file):
            logging.error("Input file not found %s" % (input_file))
            return None

        try:
            input_file_handle = open(input_file)
        except Exception as e:
            logging.error("Can not read from %s" % (input_file))
            return None

        return input_file_handle
