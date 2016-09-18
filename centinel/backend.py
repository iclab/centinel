from base64 import urlsafe_b64encode
import glob
import json
import logging
import os
import re
import requests
import time
import uuid

import centinel.utils as utils


logging.getLogger("requests").setLevel(logging.WARNING)


class User:
    def __init__(self, config):
        self.config = config
        self.verify = self.config['server']['verify']
        # check for login file
        if os.path.isfile(config['server']['login_file']):
            with open(config['server']['login_file']) as login_fh:
                login_details = json.load(login_fh)
                self.username = login_details.get('username')
                self.password = login_details.get('password')
                self.typeable_handle = login_details.get('typeable_handle')
                self.auth = (self.username, self.password)
        else:
            self.create_user()

    def request(self, slug):
        url = "%s/%s" % (self.config['server']['server_url'], slug)
        try:
            req = requests.get(url, auth=self.auth,
                               proxies=self.config['proxy']['proxy'],
                               verify=self.verify)
            req.raise_for_status()
            return req.json()
        except Exception as exp:
            logging.exception("Exception trying to make request - %s for URL: %s" %
                          (exp, url))
            raise exp

    @property
    def recommended_version(self):
        try:
            return int(self.request("version")["version"])
        except Exception as exp:
            logging.exception("Exception trying to get recommended version: %s " %
                          (exp))
            raise exp

    @property
    def experiments(self):
        try:
            return self.request("experiments")["experiments"]
        except Exception as exp:
            logging.exception("Error trying to get experiments: %s " % (exp))
            raise exp

    @property
    def input_files(self):
        try:
            return self.request("input_files")["inputs"]
        except Exception as exp:
            logging.exception("Error trying to get input files: %s " % (exp))
            raise exp

    @property
    def results(self):
        try:
            return self.request("results")
        except Exception as exp:
            logging.exception("Error trying to get results: %s " % (exp))
            raise exp

    @property
    def clients(self):
        try:
            return self.request("clients")
        except Exception as exp:
            logging.exception("Error trying to get clients: %s " % (exp))
            raise exp

    def submit_result(self, file_name):
        logging.info("Uploading result file - %s", file_name)

        with open(file_name) as result_file:
            files = {'result': result_file}
            url = "%s/%s" % (self.config['server']['server_url'], "results")
            timeout = self.config['server']['req_timeout']
            try:
                req = requests.post(url, files=files, auth=self.auth,
                                    proxies=self.config['proxy']['proxy'],
                                    timeout=timeout,
                                    verify=self.verify)
                req.raise_for_status()
                if ('delete_after_sync' in self.config['results'].keys()
                   and self.config['results']['delete_after_sync']):
                    os.remove(file_name)
            except Exception as exp:
                logging.exception("Error trying to submit result: %s" % exp)

    def sync_scheduler(self):
        """Download the scheduler.info file and perform a smart comparison
        with what we currently have so that we don't overwrite the
        last_run timestamp

        To do a smart comparison, we go over each entry in the
        server's scheduler file. If a scheduler entry is not present
        in the server copy, we delete it in the client copy and if the
        scheduler entry is present in the server copy, then we
        overwrite the frequency count in the client copy

        """
        # get the server scheduler.info file
        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "experiments", "scheduler.info")
        try:
            req = requests.get(url, proxies=self.config['proxy']['proxy'],
                               auth=self.auth,
                               verify=self.verify)
            req.raise_for_status()
        except Exception as exp:
            logging.exception("Error trying to download scheduler.info: %s" % exp)
            raise exp

        try:
            server_sched = json.loads(req.content)
        except Exception as exp:
            logging.exception("Error parsing server scheduler: %s" % exp)
            raise exp

        sched_filename = os.path.join(self.config['dirs']['experiments_dir'],
                                      'scheduler.info')
        if not os.path.exists(sched_filename):
            with open(sched_filename, 'w') as file_p:
                json.dump(server_sched, file_p, indent=2,
                      separators=(',', ': '))
            return

        client_sched = {}
        try:
            with open(sched_filename, 'r') as file_p:
                client_sched = json.load(file_p)
        except Exception as exp:
            client_sched = {}
            logging.exception("Error loading scheduler file: %s" % exp)
            logging.info("Making an empty scheduler")

        # delete any scheduled tasks as necessary
        #
        # Note: this looks ugly, but we can't modify dictionaries
        # while we iterate over them
        client_exp_keys = client_sched.keys()
        for exp in client_exp_keys:
            if exp not in server_sched:
                del client_sched[exp]
        # and update all the other frequencies
        for exp in server_sched:
            if exp in client_sched:
                client_sched[exp]['frequency'] = server_sched[exp]['frequency']
            else:
                client_sched[exp] = server_sched[exp]

        # write out the results
        with open(sched_filename, 'w') as file_p:
            json.dump(client_sched, file_p, indent=2,
                      separators=(',', ': '))

    def download_experiment(self, name):
        logging.info("Downloading experiment - %s", name)

        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "experiments", name)
        try:
            req = requests.get(url, proxies=self.config['proxy']['proxy'],
                               auth=self.auth,
                               verify=self.verify)
            req.raise_for_status()
        except Exception as exp:
            logging.exception("Error trying to download experiments: %s" % exp)
            raise exp

        name = "%s" % name
        with open(os.path.join(self.config['dirs']['experiments_dir'], name),
                  "w") as exp_fh:
            exp_fh.write(req.content)

    def download_input_file(self, name):
        logging.info("Downloading input data file - %s", name)

        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "input_files", name)
        try:
            req = requests.get(url, proxies=self.config['proxy']['proxy'],
                               auth=self.auth,
                               verify=self.verify)
            req.raise_for_status()
        except Exception as exp:
            logging.exception("Error trying to download experiments: %s" % exp)
            raise exp

        name = "%s" % name
        with open(os.path.join(self.config['dirs']['data_dir'], name),
                  "w") as exp_fh:
            exp_fh.write(req.content)

    def register(self, username, password):
        logging.info("Registering new user %s" % (username))

        url = "%s/%s" % (self.config['server']['server_url'], "register")
        payload = {'username': username, 'password': password,
                   'is_vpn': self.config['user'].get('is_vpn')}
        headers = {'content-type': 'application/json'}
        try:
            req = requests.post(url, data=json.dumps(payload),
                                proxies=self.config['proxy']['proxy'],
                                headers=headers,
                                verify=self.verify)
            req.raise_for_status()
            return req.json()
        except Exception as exp:
            logging.exception("Error trying to submit registration URL: %s " % exp)
            raise exp

    def set_country(self, country):
        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "set_country", country)
        try:
            req = requests.get(url,
                               auth=self.auth,
                               proxies=self.config['proxy']['proxy'],
                               verify=self.verify)
            req.raise_for_status()
            return req.json()
        except Exception as exp:
            logging.exception("Error trying to set country: %s " % exp)
            raise exp

    def set_ip(self, ip):
        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "set_ip", ip)
        try:
            req = requests.get(url,
                               auth=self.auth,
                               proxies=self.config['proxy']['proxy'],
                               verify=self.verify)
            req.raise_for_status()
            return req.json()
        except Exception as exp:
            logging.exception("Error trying to set ip: %s " % exp)
            raise exp

    def create_user(self):
        self.username = str(uuid.uuid4())
        self.password = os.urandom(64).encode('base-64')
        self.auth = (self.username, self.password)
        self.typeable_handle = None

        try:
            register_results = self.register(self.username, self.password)
            if 'typeable_handle' in register_results.keys():
                self.typeable_handle = register_results['typeable_handle']
            with open(self.config['server']['login_file'], "w") as login_fh:
                login_details = {'username': self.username,
                                 'password': self.password}
                if self.typeable_handle is not None:
                    login_details['typeable_handle'] = self.typeable_handle
                json.dump(login_details, login_fh, indent=2,
                      separators=(',', ': '))
        except Exception as exp:
            logging.exception("Unable to register: %s" % str(exp))
            raise exp

    def informed_consent(self):
        """Create a URL for the user to give their consent through"""
        if self.typeable_handle is None:
            consent_url = [self.config['server']['server_url'],
                           "/get_initial_consent?username="]
            consent_url.append(urlsafe_b64encode(self.username))
            consent_url.append("&password=")
            consent_url.append(urlsafe_b64encode(self.password))
        else:
            consent_url = [self.config['server']['server_url'],
                           "/consent/"]
            consent_url.append(self.typeable_handle)

        consent_url = "".join(consent_url)
        print "Please go to %s to give your consent." % (consent_url)
        return consent_url


def sync(config):
    logging.info("Starting sync with %s", config['server']['server_url'])

    start = time.time()
    try:
        user = User(config)
    except Exception, exp:
        logging.exception("Unable to create user: %s" % str(exp))
        return

    # send all results (.bz2)
    result_files = glob.glob(os.path.join(config['dirs']['results_dir'],
                                          '[!_]*.bz2'))

    # only upload pcaps if it is allowed
    if config['results']['upload_pcaps'] is False:
        for pcap_file in glob.glob(os.path.join(config['dirs']['results_dir'],
                                                '[!_]*.pcap.bz2')):
            if pcap_file in result_files:
                result_files.remove(pcap_file)

    for path in result_files:
        try:
            user.submit_result(path)
        except Exception, exp:
            if re.search("418", str(exp)) is not None:
                logging.error("You have not completed the informed consent "
                              "and will be unable to submit results or get "
                              "new experiments until you do.")
                user.informed_consent()
                return
            else:
                logging.error("Unable to send result file: %s" % str(exp))
            raise exp
        if time.time() - start > config['server']['total_timeout']:
            logging.error("Interaction with server took too long. Preempting")
            return

    # determine how to sync the experiment files
    # Note: we are not checking anything that starts with _
    client_exps = utils.hash_folder(config['dirs']['experiments_dir'],
                                    '[!_]*')
    try:
        server_exps = user.experiments
    except Exception as exp:
        if re.search("418", str(exp)) is not None:
            logging.error("You have not completed the informed consent and "
                          "will be unable to submit results or get new "
                          "experiments until you do.")
            user.informed_consent()
            return
        else:
            logging.error("Error collecting experiments: %s" % exp)
        raise exp
    if time.time() - start > config['server']['total_timeout']:
        logging.error("Interaction with server took too long. Preempting")
        return

    dload_exps, del_exps = utils.compute_files_to_download(client_exps,
                                                           server_exps)

    # delete the files that aren't on the server
    for exp_file in del_exps:
        filename = os.path.join(config['dirs']['experiments_dir'], exp_file)
        os.remove(filename)
    # get the files that have changed or we don't have
    for exp_file in dload_exps:
        try:
            if exp_file != "scheduler.info":
                user.download_experiment(exp_file)
            else:
                try:
                    user.sync_scheduler()
                except Exception as e:
                    logging.exception("Scheduler sync failed: %s", str(e))
        except Exception as e:
            logging.exception("Unable to download experiment file: %s", str(e))

        if time.time() - start > config['server']['total_timeout']:
            logging.error("Interaction with server took too long. Preempting")
            return

    # determine how to sync the input files
    client_inputs = utils.hash_folder(config['dirs']['data_dir'], '[!_]*')
    try:
        server_inputs = user.input_files
    except Exception as exp:
        logging.exception("Unable to retrive user inputs due to Exception: "
                      "%s. Preempting" % exp)
        return

    if time.time() - start > config['server']['total_timeout']:
        logging.error("Interaction with server took too long. Preempting")
        return

    dload_inputs, del_inputs = utils.compute_files_to_download(client_inputs,
                                                               server_inputs)

    # delete the files that aren't on the server
    for input_file in del_inputs:
        filename = os.path.join(config['dirs']['data_dir'], input_file)
        os.remove(filename)
    # get the files that have changed or we don't have
    for input_file in dload_inputs:
        try:
            user.download_input_file(input_file)
        except Exception, e:
            logging.exception("Unable to download input file %s", str(e))
        if time.time() - start > config['server']['total_timeout']:
            logging.error("Interaction with server took too long. Preempting")
            return

    logging.info("Finished sync with %s", config['server']['server_url'])


def set_vpn_info(config, ip=None, country=None):
    logging.info("Setting country as "
                 "%s and IP address as %s" % (country, ip))
    try:
        user = User(config)
    except Exception as exp:
        logging.exception("Unable to create user: %s" % str(exp))
        return False

    if country is not None:
        user.set_country(country)

    if ip is not None:
        user.set_ip(ip)


def get_meta(config, ip=''):
    url = "%s/%s/%s" % (config['server']['server_url'],
                        "meta", ip)
    try:
        req = requests.get(url,
                           proxies=config['proxy']['proxy'],
                           verify=config['server']['verify'],
                           timeout=10)
        req.raise_for_status()
        return req.json()
    except Exception as exp:
        logging.exception("Error trying to get metadata: %s " % exp)
        raise exp
