import bz2
import glob
import imp
import json
import logging
import logging.config
import os
import tarfile
import time

from datetime import datetime

from experiment import Experiment, ExperimentList

from centinel.backend import get_meta
from centinel.primitives.tcpdump import Tcpdump

loaded_modules = set()


class Client():

    def __init__(self, config):
        self.config = config
        self.experiments = self.load_experiments()
        self._meta = None

    def setup_logging(self):

        log_config = {'version':1,
                      'formatters':{'error':{'format':self.config['log']['log_format']},
                                    'debug':{'format':self.config['log']['log_format']}},
                      'handlers':{'console':{'class':'logging.StreamHandler',
                                             'formatter':'debug',
                                             'level':self.config['log']['log_level']},
                                  'file':{'class':'logging.FileHandler',
                                          'filename':self.config['log']['log_file'],
                                          'formatter':'error',
                                          'level': self.config['log']['log_level']}},
                      'root':{'handlers':('console', 'file'), 'level':self.config['log']['log_level']}}
        logging.config.dictConfig(log_config)

        logging.debug("Finished setting up logging.")

    def get_result_file(self, name, start_time):
        result_file = "%s-%s.json.bz2" % (name, start_time)
        return os.path.join(self.config['dirs']['results_dir'], result_file)

    def get_input_file(self, experiment_name):
        input_file = "%s" % (experiment_name)
        return os.path.join(self.config['dirs']['data_dir'], input_file)

    def load_input_file(self, name):
        input_file = self.get_input_file(name)

        if not os.path.isfile(input_file):
            logging.error("Input file not found %s" % (input_file))
            return None

        try:
            input_file_handle = open(input_file)
        except Exception as exp:
            logging.exception("Can not read from %s: %s" % (input_file, str(exp)))
            return None
        logging.debug("Input file %s loaded." % (name))
        return input_file_handle

    def load_experiments(self):
        """This function will return the list of experiments.
        """
        logging.debug("Loading experiments.")
        # look for experiments in experiments directory
        exp_dir = self.config['dirs']['experiments_dir']
        for path in glob.glob(os.path.join(exp_dir, '[!_]*.py')):
            # get name of file and path
            name, ext = os.path.splitext(os.path.basename(path))
            # load the experiment
            try:
                # do not load modules that have already been loaded
                if name in loaded_modules:
                    continue
                imp.load_source(name, path)
                loaded_modules.add(name)
                logging.debug("Loaded experiment \"%s(%s)\"." % (name, path))
            except Exception as exception:
                logging.exception("Failed to load experiment %s: %s" %
                              (name, exception))

        logging.debug("Finished loading experiments.")
        # return dict of experiment names and classes
        return ExperimentList.experiments

    def has_experiments_to_run(self):
        # load scheduler information
        sched_filename = os.path.join(self.config['dirs']['experiments_dir'],
                                      'scheduler.info')
        sched_info = {}
        if os.path.exists(sched_filename):
            with open(sched_filename, 'r') as file_p:
                sched_info = json.load(file_p)

        for name in sched_info:
            run_next = sched_info[name]['last_run']
            run_next += sched_info[name]['frequency']
            if run_next <= time.time():
                logging.debug("Client has experiment(s) to run (%s)." % (name))
                return True
        logging.debug("Client has no experiments to run.")
        return False


    def get_meta(self):
        """we only want to get the meta information (our normalized IP) once,
        so we are going to do lazy instantiation to improve performance

        """
        # get the normalized IP if we don't already have it
        if self._meta is None:
            self._meta = get_meta(self.config)
        return self._meta

    def run(self, data_dir=None):

        """
        Note: this function will check the experiments directory for a
        special file, scheduler.info, that details how often each
        experiment should be run and the last time the experiment was
        run. If the time since the experiment was run is shorter than
        the scheduled interval in seconds, then the experiment will
        not be run.

        """
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
        logging.debug("Results directory: %s" % (self.config['dirs']['results_dir']))

        experiments_set = self.experiments.items()

        # load scheduler information
        sched_filename = os.path.join(self.config['dirs']['experiments_dir'],
                                      'scheduler.info')

        logging.debug("Loading scheduler file.")
        sched_info = {}
        if os.path.exists(sched_filename):
            with open(sched_filename, 'r') as file_p:
                try:
                    sched_info = json.load(file_p)
                except Exception as exp:
                    logging.error("Failed to load the "
                                  "scheduler: %s" % str(exp))
                    return

        logging.debug("Scheduler file loaded.")

        logging.debug("Processing the experiment schedule.")
        for name in sched_info:

            # check if we should preempt on the experiment (if the
            # time to run next is greater than the current time) and
            # store the last run time as now
            #
            # Note: if the experiment is not in the scheduler, then it
            # will not be run at all.
            run_next = sched_info[name]['last_run']
            run_next += sched_info[name]['frequency']
            if run_next > time.time():
                run_next_str = datetime.fromtimestamp(long(run_next))
                logging.debug("Skipping %s, it will "
                              "be run on or after %s." % (name, run_next_str))
                continue

            # backward compatibility with older-style scheduler
            if 'python_exps' not in sched_info[name]:
                self.run_exp(name)
            else:
                exps = sched_info[name]['python_exps'].items()
                for python_exp, exp_config in exps:
                    logging.debug("Running %s." % (python_exp))
                    self.run_exp(python_exp, exp_config, schedule_name=name)
                    logging.debug("Finished running %s." % (python_exp))
            sched_info[name]['last_run'] = time.time()

        logging.debug("Updating timeout values in scheduler.")
        # write out the updated last run times
        with open(sched_filename, 'w') as file_p:
            json.dump(sched_info, file_p, indent=2,
                      separators=(',', ': '))

        self.consolidate_results()

        logging.info("Finished running experiments. "
                     "Look in %s for results." % (self.config['dirs']['results_dir']))

    def run_exp(self, name, exp_config=None, schedule_name=None):
        if name not in self.experiments:
            logging.error("Experiment file %s not found! Skipping." % (name))
        else:
            Exp = self.experiments[name]
            results = {}

            results["meta"] = {}
            try:
                logging.debug("Getting metadata for experiment...")
                meta = self.get_meta()
                results["meta"] = meta
            except Exception as exception:
                logging.exception("Error fetching metadata for "
                              "%s: %s" % (name, exception))
                results["meta_exception"] = str(exception)

            if schedule_name is not None:
                results["meta"]["schedule_name"] = schedule_name
            else:
                results["meta"]["schedule_name"] = name

            start_time = datetime.now()
            results["meta"]["client_time"] = start_time.isoformat()

            input_files = {}
            if exp_config is not None:
                if (('input_files' in exp_config) and
                   (exp_config['input_files'] is not None)):
                    for filename in exp_config['input_files']:
                        file_handle = self.load_input_file(filename)
                        if file_handle is not None:
                            input_files[filename] = file_handle
                if (('params' in exp_config) and
                   (exp_config['params'] is not None)):
                    Exp.params = exp_config['params']

            # if the experiment specifies a list of input file names,
            # load them. failing to load input files does not stop
            # experiment from running.
            if Exp.input_files is not None:
                for filename in Exp.input_files:
                    file_handle = self.load_input_file(filename)
                    if file_handle is not None:
                        input_files[filename] = file_handle
            # otherwise, fall back on [experiment name].txt
            else:
                input_files = self.load_input_file("%s.txt" % (name))

            try:
                # instantiate the experiment
                logging.debug("Initializing the experiment class for %s" % (name))
                exp = Exp(input_files)
            except Exception as exception:
                logging.exception("Error initializing %s: %s" % (name, exception))
                results["init_exception"] = str(exception)
                return

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
            except Exception as exp:
                logging.exception("Failed to run tcpdump: %s" % (exp,))

            try:
                # run the experiment
                exp.run()
            except Exception as exception:
                logging.exception("Error running %s: %s" % (name, exception))
                results["runtime_exception"] = str(exception)

            # save any external results that the experiment has generated
            # they could be anything that doesn't belong in the json file
            # (e.g. pcap files)
            # these should all be compressed with bzip2
            # the experiment is responsible for giving these a name and
            # keeping a list of files in the json results
            results_dir = self.config['dirs']['results_dir']
            if exp.external_results is not None:
                logging.debug("Writing external files for %s" % (name))
                for fname, fcontents in exp.external_results.items():
                    external_file_name = ("external_%s-%s-%s"
                                          ".bz2" % (name,
                                                    start_time.isoformat(),
                                                    fname))
                    external_file_path = os.path.join(results_dir,
                                                      external_file_name)
                    try:
                        with open(external_file_path, 'w:bz2') as file_p:
                            data = bz2.compress(fcontents)
                            file_p.write(data)
                            logging.debug("External file "
                                          "%s written successfully" % (fname))
                    except Exception as exp:
                        logging.exception("Failed to write external file:"
                                        "%s" % (exp))
                logging.debug("Finished writing external files for %s" % (name))

            if tcpdump_started:
                logging.info("Waiting for tcpdump to process packets...")
                # 5 seconds should be enough. this hasn't been tested on
                # a RaspberryPi or a Hummingboard i2
                time.sleep(5)
                td.stop()
                logging.info("tcpdump stopped.")
                try:
                    pcap_file_name = ("pcap_%s-%s.pcap"
                                      ".bz2" % (name, start_time.isoformat()))
                    pcap_file_path = os.path.join(results_dir,
                                                  pcap_file_name)

                    with open(pcap_file_path, 'w:bz2') as file_p:
                        data = bz2.compress(td.pcap())
                        file_p.write(data)
                        logging.info("Saved pcap to "
                                     "%s." % (pcap_file_path))
                except Exception as exception:
                    logging.exception("Failed to write pcap file: %s" %
                                    (exception))

            # close input file handle(s)
            logging.debug("Closing input files for %s" % (name))
            if type(input_files) is dict:
                for file_name, file_handle in input_files.items():
                    file_handle.close()
            else:
                input_files.close()
            logging.debug("Input files closed for %s" % (name))

            logging.debug("Storing results for %s" % (name))
            try:
                results[name] = exp.results
            except Exception as exception:
                logging.exception("Error storing results for "
                              "%s: %s" % (name, exception))
                results["results_exception"] = str(exception)

            end_time = datetime.now()
            time_taken = (end_time - start_time)
            results["meta"]["time_taken"] = time_taken.total_seconds()

            logging.info("%s took %s to finish." % (name, time_taken))

            logging.debug("Saving %s results to file" % (name))
            try:
                # Pretty printing results will increase file size, but files are
                # compressed before sending.
                result_file_path = self.get_result_file(name,
                                                        start_time.isoformat())
                result_file = bz2.BZ2File(result_file_path, "w")
                json.dump(results, result_file, indent=2,
                          separators=(',', ': '))
                result_file.close()
            except Exception as exception:
                logging.exception("Error saving results for "
                              "%s to file: %s" % (name, exception))
                results["results_exception"] = str(exception)
            logging.debug("Done saving %s results to file" % (name))

    def consolidate_results(self):
        # bundle and compress result files
        result_files = [path for path in glob.glob(
            os.path.join(self.config['dirs']['results_dir'], '*.json.bz2'))]

        if len(result_files) >= self.config['results']['files_per_archive']:
            logging.info("Compressing and archiving results.")

            files_archived = 0
            archive_count = 0
            tar_file = None
            files_per_archive = self.config['results']['files_per_archive']
            results_dir = self.config['dirs']['results_dir']
            for path in result_files:
                if (files_archived % files_per_archive) == 0:
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

                tar_file.add(path, arcname=os.path.basename(path))
                os.remove(path)
                files_archived += 1

            if tar_file:
                tar_file.close()
