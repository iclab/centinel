import glob
import imp
import json
import logging
import logging.config
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from select import PIPE_BUF

import centinel
from centinel.backend import get_meta
from centinel.primitives.tcpdump import Tcpdump
from experiment import ExperimentList
from centinel.vpn.cli import get_external_ip

loaded_modules = set()
# we need a global reference to stop it if we receive an interrupt.
tds = []

def signal_handler(signal, frame):
    logging.warn('Interrupt signal received.')
    if len(tds) > 0:
        logging.warn('Stopping TCP dump...')
        for td in tds:
            td.stop()
            td.delete()
    logging.warn('Exiting...')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

# this entire class can be replaced with a call to lzma.open() when we
# drop support for python2.  it only supports "w" and "wb" modes (which
# are treated the same)
class LZMAFile:
    def __init__(self, name, mode):
        if mode not in ("w", "wb"):
            raise NotImplementedError

        self.mode = mode
        self.name = name
        self.softspace = 0
        self._cmd = ["xz", "-9"]

        fd = os.open(name, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 438) # 0o666
        try:
            self._proc = subprocess.Popen(self._cmd,
                                          stdin=subprocess.PIPE,
                                          stdout=fd)
            self._f = self._proc.stdin
        finally:
            # once 'proc' has started, we don't need to hold on to our
            # handle to the output file anymore
            os.close(fd)

    def __enter__(self):
        return self

    def __exit__(self, *dontcare):
        self.close()
        return False

    def __iter__(self):
        return self

    # file API:
    def close(self):
        if self._f is not None:
            try:
                self._f.close()
                if self._proc.wait() != 0:
                    raise subprocess.CalledProcessError(
                        self._proc.returncode,
                        self._cmd + [">", self.name]
                    )
            finally:
                self._f = None
                self._proc = None

    @property
    def closed(self):
        return self._f is None

    @property
    def newlines(self):
        return None

    # Methods that take arguments forward to _f using the completely
    # generic '*a, **k' mechanism so that argument processing behavior
    # will exactly match a real file object.
    # fileno() not provided
    def flush(self):               return self._f.flush()
    # isatty() not provided
    def next(self):                return self._f.next()
    def read(self, *a, **k):       return self._f.read(*a, **k)
    def readline(self, *a, **k):   return self._f.readline(*a, **k)
    def readlines(self, *a, **k):  return self._f.readlines(*a, **k)
    def seek(self, *a, **k):       return self._f.seek(*a, **k)
    def tell(self):                return self._f.tell()
    def truncate(self, *a, **k):   return self._f.truncate(*a, **k)
    def write(self, *a, **k):      return self._f.write(*a, **k)
    def writelines(self, *a, **k): return self._f.writelines(*a, **k)
    # xreadlines does not forward because that would expose _f
    def xreadlines(self):          return self.__iter__()


class Client:
    def __init__(self, config, vpn_provider=None):
        self.config = config
        self.experiments = self.load_experiments()
        self._meta = None
        self.vpn_provider = vpn_provider

    def setup_logging(self):

        log_config = {'version': 1,
                      'formatters': {'error': {'format': self.config['log']['log_format']},
                                     'debug': {'format': self.config['log']['log_format']}},
                      'handlers': {'console': {'class': 'logging.StreamHandler',
                                               'formatter': 'debug',
                                               'level': self.config['log']['log_level']},
                                   'file': {'class': 'logging.FileHandler',
                                            'filename': self.config['log']['log_file'],
                                            'formatter': 'error',
                                            'level': self.config['log']['log_level']}},
                      'root': {'handlers': ('console', 'file'), 'level': self.config['log']['log_level']}}
        logging.config.dictConfig(log_config)

        logging.debug("Finished setting up logging.")

    def get_result_file(self, name, start_time):
        result_file = "%s-%s.json.xz" % (name, start_time)
        return os.path.join(self.config['dirs']['results_dir'], result_file)

    def get_input_file(self, experiment_name):
        input_file = "%s" % experiment_name
        return os.path.join(self.config['dirs']['data_dir'], input_file)

    def load_input_file(self, name):
        input_file = self.get_input_file(name)

        if not os.path.isfile(input_file):
            logging.error("Input file not found %s" % input_file)
            return None

        try:
            input_file_handle = open(input_file)
        except Exception as exp:
            logging.exception("Can not read from %s: %s" % (input_file, str(exp)))
            return None
        logging.debug("Input file %s loaded." % name)
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
                logging.debug("Client has experiment(s) to run (%s)." % name)
                return True
        logging.debug("Client has no experiments to run.")
        return False

    def get_meta(self):
        """we only want to get the meta information (our normalized IP) once,
        so we are going to do lazy instantiation to improve performance

        """
        # get the normalized IP if we don't already have it
        if self._meta is None:
            external_ip = get_external_ip()
            if external_ip:
                self._meta = get_meta(self.config, external_ip)
            else:
                raise Exception("Unable to get public IP")
            if 'custom_meta' in self.config:
                self._meta['custom_meta'] = self.config['custom_meta']

        return self._meta

    def run(self, data_dir=None):

        """
        Note: this function will check the experiments directory for a
        special file, scheduler.info, that details how often each
        experiment should be run and the last time the experiment was
        run. If the time since the experiment was run is shorter than
        the scheduled interval in seconds, then the experiment will
        not be run.

        :param data_dir:
        :return:
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
                self.run_exp(name=name)
            else:
                exps = sched_info[name]['python_exps'].items()
                for python_exp, exp_config in exps:
                    logging.debug("Running %s." % python_exp)
                    self.run_exp(name=python_exp, exp_config=exp_config, schedule_name=name)
                    logging.debug("Finished running %s." % python_exp)
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
        if name[-3:] == ".py":
            name = name[:-3]
        if name not in self.experiments:
            logging.error("Experiment file %s not found! Skipping." % name)
        else:
            exp_class = self.experiments[name]
            results = {"meta": {}}
            try:
                logging.debug("Getting metadata for experiment...")
                meta = self.get_meta()
                results["meta"] = meta
            except Exception as exception:
                logging.exception("Error fetching metadata for "
                                  "%s: %s" % (name, exception))
                results["meta_exception"] = str(exception)
		
            if 'country' in results['meta']:
		results['meta']['maxmind_country'] = results['meta']['country']
	    if 'hostname' in self.configs['user']:
		results['meta']['vpn_name'] = self.configs['user']['hostname']
	    if 'connected_ip' in self.configs['user']:
                results['meta']['vpn_ip'] = self.configs['user']['connected_ip']
	    if 'claimed_country' in self.configs['user']:
		results['meta']['country'] = self.configs['user']['claimed_country']

            if schedule_name is not None:
                results["meta"]["schedule_name"] = schedule_name
            else:
                results["meta"]["schedule_name"] = name

            start_time = datetime.now()
            results["meta"]["client_time"] = start_time.isoformat()

            results["meta"]["centinel_version"] = centinel.__version__

            # include vpn provider in metadata
            if self.vpn_provider:
                results["meta"]["vpn_provider"] = self.vpn_provider

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
                    exp_class.params = exp_config['params']

            # if the scheduler does not specify input files, but
            # the experiment class specifies a list of input file names,
            # load them. failing to load input files does not stop
            # experiment from running.
            if len(input_files) == 0:
                if exp_class.input_files is not None:
                    for filename in exp_class.input_files:
                        file_handle = self.load_input_file(filename)
                        if file_handle is not None:
                            input_files[filename] = file_handle
                # otherwise, fall back to [schedule name].txt (deprecated)
                else:
                    filename = "%s.txt" % name
                    file_handle = self.load_input_file(filename)
                    if file_handle is not None:
                        input_files[filename] = file_handle

            try:
                # instantiate the experiment
                logging.debug("Initializing the experiment class for %s" % name)

                # these constants can be useful for some experiments, but it is not
                # encouraged to use these directly
                global_constants = {'experiments_dir': self.config['dirs']['experiments_dir'],
                                    'results_dir': self.config['dirs']['results_dir'],
                                    'data_dir': self.config['dirs']['data_dir']}

                exp_class.global_constants = global_constants

                exp = exp_class(input_files)
            except Exception as exception:
                logging.exception("Error initializing %s: %s" % (name, exception))
                results["init_exception"] = str(exception)
                return

            exp.global_constants = global_constants

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

            if run_tcpdump and exp_class.overrides_tcpdump:
                logging.info("Experiment overrides tcpdump recording.")
                run_tcpdump = False

            tcpdump_started = False

            try:
                if run_tcpdump:
                    td = Tcpdump()
                    tds.append(td)
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
            except KeyboardInterrupt:
                logging.warn("Keyboard interrupt received, stopping experiment...")


            # save any external results that the experiment has generated
            # they could be anything that doesn't belong in the json file
            # (e.g. pcap files)
            # these should all be compressed
            # the experiment is responsible for giving these a name and
            # keeping a list of files in the json results
            results_dir = self.config['dirs']['results_dir']
            if exp.external_results is not None:
                logging.debug("Writing external files for %s" % name)
                for fname, fcontents in exp.external_results.items():
                    external_file_name = "external_%s-%s-%s.xz" % (
                        name,
                        start_time.strftime("%Y-%m-%dT%H%M%S.%f"),
                        fname
                    )
                    external_file_path = os.path.join(results_dir,
                                                      external_file_name)
                    try:
                        with LZMAFile(external_file_path, 'wb') as file_p:
                            if isinstance(fcontents, unicode):
                                file_p.write(fcontents.encode("utf-8"))
                            else:
                                file_p.write(fcontents)
                    except Exception as exp:
                        logging.exception("Failed to write external file:"
                                          "%s" % exp)
                    else:
                        logging.debug("External file %s written successfully"
                                      % fname)
                logging.debug("Finished writing external files for %s" % name)

            if tcpdump_started:
                logging.info("Waiting for tcpdump to process packets...")
                # 5 seconds should be enough. this hasn't been tested on
                # a RaspberryPi or a Hummingboard i2
                time.sleep(5)
                td.stop()
                logging.info("tcpdump stopped.")

                pcap_file_name = "pcap_%s-%s.pcap.xz" % (
                    name, start_time.strftime("%Y-%m-%dT%H%M%S.%f")
                )
                pcap_file_path = os.path.join(results_dir,
                                              pcap_file_name)
                try:
                    with open(td.pcap_filename(), 'rb') as pcap, \
                         LZMAFile(pcap_file_path, 'wb') as pcap_compress: \

                         for chunk in iter(lambda: pcap.read(PIPE_BUF), b''):
                             pcap_compress.write(chunk)

                except Exception as exception:
                    compression_successful = False
                    logging.exception("Failed to compress and write "
                                      "pcap file: %s" % exception)

                else:
                    compression_successful = True
                    uncompressed_size = os.path.getsize(td.pcap_filename())
                    compressed_size = os.path.getsize(pcap_file_path)
                    compression_ratio = 100.0 * float(compressed_size) / float(uncompressed_size)
                    logging.debug("pcap LZMA compression: compressed/uncompressed (ratio):"
                                  " %d/%d (%.1f%%)" % (compressed_size, uncompressed_size, compression_ratio))
                    logging.info("Saved pcap to %s." % pcap_file_path)

                if not compression_successful:
                    logging.info("Writing pcap file uncompressed")
                    # chop off the .xz
                    pcap_file_path = pcap_file_path[:-3]
                    try:
                        shutil.copyfile(td.pcap_filename(), pcap_file_path)
                    except Exception as exception:
                        logging.exception("Failed to write "
                                          "pcap file: %s" % exception)
                    else:
                        logging.info("Saved pcap to "
                                     "%s." % pcap_file_path)

                # delete pcap data to free up some memory
                logging.debug("Removing pcap data from memory")
                td.delete()
                del data
                del td

            # close input file handle(s)
            logging.debug("Closing input files for %s" % name)
            if type(input_files) is dict:
                for file_name, file_handle in input_files.items():
                    try:
                        file_handle.close()
                    except AttributeError:
                        logging.warning("Closing %s failed" % file_name)
            logging.debug("Input files closed for %s" % name)

            logging.debug("Storing results for %s" % name)
            try:
                results[name] = exp.results
            except Exception as exception:
                logging.exception("Error storing results for "
                                  "%s: %s" % (name, exception))
                if "results_exception" not in results:
                    results["results_exception"] = {}

                results["results_exception"][name] = str(exception)

            end_time = datetime.now()
            time_taken = (end_time - start_time)
            results["meta"]["time_taken"] = time_taken.total_seconds()

            logging.info("%s took %s to finish." % (name, time_taken))

            logging.debug("Saving %s results to file" % name)
            try:
                # pretty printing results will increase file size, but files are
                # compressed before sending.
                result_file_path = self\
                    .get_result_file(name, start_time.strftime("%Y-%m-%dT%H%M%S.%f"))
                with LZMAFile(result_file_path, "w") as result_file:
                    # ignore encoding errors, these will be dealt with on the server
                    json.dump(results, result_file, indent=2, separators=(',', ': '),
                              ensure_ascii=False)
            except Exception as exception:
                logging.exception("Error saving results for "
                                  "%s to file: %s" % (name, exception))
            else:
                logging.debug("Done saving %s results to file" % name)

            # free up memory by deleting results from memory
            del results
            del result_file

    def consolidate_results(self):
        # bundle and compress result files
        result_files = [path for path in glob.glob(
            os.path.join(self.config['dirs']['results_dir'], '*.json.xz'))]

        if len(result_files) >= self.config['results']['files_per_archive']:
            logging.info("Compressing and archiving results.")

            files_archived = 0
            archive_count = 0
            tar_file = None
            files_per_archive = self.config['results']['files_per_archive']
            results_dir = self.config['dirs']['results_dir']
            for path in result_files:
                if (files_archived % files_per_archive) == 0:
                    # results files are already compressed,
                    # don't bother compressing the tarfile
                    archive_count += 1
                    archive_filename = "results-%s_%d.tar" % (
                        datetime.now().strftime("%Y-%m-%dT%H%M%S.%f"), archive_count)
                    archive_file_path = os.path.join(results_dir,
                                                     archive_filename)
                    logging.info("Creating new archive"
                                 " %s" % archive_file_path)
                    if tar_file:
                        tar_file.close()
                    tar_file = tarfile.open(archive_file_path, "w")

                tar_file.add(path, arcname=os.path.basename(path))
                os.remove(path)
                files_archived += 1

            if tar_file:
                tar_file.close()
