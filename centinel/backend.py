from base64 import urlsafe_b64encode
import glob
import json
import logging
import os
import requests
import time
import uuid


class User:
    def __init__(self, config):
        self.config = config
        # check for login file
        if os.path.isfile(config['server']['login_file']):
            with open(config['server']['login_file']) as login_fh:
                login_details = json.load(login_fh)
                self.username = login_details.get('username')
                self.password = login_details.get('password')
                self.auth     = (self.username, self.password)
        else:
            self.create_user()

    def request(self, slug):
        url = "%s/%s" % (self.config['server']['server_url'], slug)
        try:
            req = requests.get(url, auth=self.auth,
                               proxies=self.config['proxy']['proxy'],
                               verify=self.config['server']['cert_bundle'])
            req.raise_for_status()
            return req.json()
        except Exception as exp:
            logging.error("Exception trying to make request - %s for URL: %s" %
                          (exp, url))
            raise exp

    @property
    def recommended_version(self):
        try:
            return int(self.request("version")["version"])
        except Exception as exp:
            logging.error("Exception trying to get recommended version: %s " %
                          (exp))
            raise exp

    @property
    def experiments(self):
        try:
            return self.request("experiments")["experiments"]
        except Exception as exp:
            logging.error("Error trying to get experiments: %s " % (exp))
            raise exp

    @property
    def input_files(self):
        try:
            return self.request("input_files")["input_files"]
        except Exception as exp:
            logging.error("Error trying to get input files: %s " % (exp))
            raise exp

    @property
    def results(self):
        try:
            return self.request("results")
        except Exception as exp:
            logging.error("Error trying to get results: %s " % (exp))
            raise exp

    @property
    def clients(self):
        try:
            return self.request("clients")
        except Exception as exp:
            logging.error("Error trying to get clients: %s " % (exp))
            raise exp

    def submit_result(self, file_name):
        logging.info("Uploading result file - %s", file_name)

        with open(file_name) as result_file:
            files   = {'result': result_file}
            url     = "%s/%s" % (self.config['server']['server_url'],
                                 "results")
            timeout = self.config['server']['req_timeout']
            cert_bundle = self.config['server']['cert_bundle']
            try:
                req = requests.post(url, files=files, auth=self.auth,
                                    proxies=self.config['proxy']['proxy'],
                                    timeout=timeout, verify=cert_bundle)
                req.raise_for_status()
                os.remove(file_name)
            except Exception as exp:
                logging.error("Error trying to submit result: %s" % exp)
                raise exp

    def download_experiment(self, name):
        logging.info("Downloading experiment - %s", name)

        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "experiments", name)
        try:
            req = requests.get(url, proxies=self.config['proxy']['proxy'],
                               verify=self.config['server']['cert_bundle'],
                               auth=self.auth)
            req.raise_for_status()
        except Exception as exp:
            logging.error("Error trying to download experiments: %s" % exp)
            raise exp

        name = "%s.py" % name
        with open(os.path.join(self.config['dirs']['experiments_dir'], name),
                  "w") as exp_fh:
            exp_fh.write(req.content)

    def download_input_file(self, name):
        logging.info("Downloading input data file - %s", name)

        url = "%s/%s/%s" % (self.config['server']['server_url'],
                            "input_files", name)
        try:
            req = requests.get(url, proxies=self.config['proxy']['proxy'],
                               verify=self.config['server']['cert_bundle'],
                               auth=self.auth)
            req.raise_for_status()
        except Exception as exp:
            logging.error("Error trying to download experiments: %s" % exp)
            raise exp

        name = "%s.py" % name
        with open(os.path.join(self.config['dirs']['data_dir'], name),
                  "w") as exp_fh:
            exp_fh.write(req.content)

    def register(self, username, password):
        logging.info("Registering new user %s" % (username))

        url     = "%s/%s" % (self.config['server']['server_url'], "register")
        payload = {'username': username, 'password': password,
                   'is_vpn': self.config['user'].get('is_vpn')}
        headers = {'content-type': 'application/json'}
        try:
            req = requests.post(url, data=json.dumps(payload),
                                proxies=self.config['proxy']['proxy'],
                                headers=headers,
                                verify=self.config['server']['cert_bundle'])
            req.raise_for_status()
        except Exception as exp:
            logging.error("Error trying to submit registration URL: %s " % exp)
            raise exp

    def create_user(self):
        self.username = str(uuid.uuid4())
        self.password = os.urandom(64).encode('base-64')
        self.auth     = (self.username, self.password)

        try:
            self.register(self.username, self.password)
            with open(self.config['server']['login_file'], "w") as login_fh:
                login_details = {'username': self.username,
                                 'password': self.password}
                json.dump(login_details, login_fh)
        except Exception as exp:
            logging.error("Unable to register: %s" % str(exp))
            raise exp

    def informed_consent(self):
        """Create a URL for the user to give their consent through"""

        consent_url = [self.config['server']['server_url'],
                       "/get_initial_consent?username="]
        consent_url.append(urlsafe_b64encode(self.username))
        consent_url.append("&password=")
        consent_url.append(urlsafe_b64encode(self.password))
        consent_url = "".join(consent_url)
        print "Please go to %s to give your consent" % (consent_url)
        return consent_url


def sync(config):
    logging.info("Starting sync with %s", config['server']['server_url'])

    start = time.time()
    try:
        user = User(config)
    except Exception, exp:
        logging.error("Unable to create user: %s" % str(exp))
        return

    # send all results
    for path in glob.glob(os.path.join(config['dirs']['results_dir'],
        '[!_]*.tar.bz2')):
        try:
            user.submit_result(path)
        except Exception, exp:
            logging.error("Unable to send result file: %s" % str(exp))
            break
        if time.time() - start > config['server']['total_timeout']:
            logging.error("Interaction with server took too long. Preempting")
            return

    # determine how to sync the experiment files
    client_exps = utils.hash_folder(config['dirs']['experiments_dir'], '[!_]*.*'):
    try:
        server_exps = user.experiments
    except Exception as exp:
        logging.error("Unable to retrive user experiments due to Exception: "
                      "%s. Preempting" % exp)
        return
    if time.time() - start > config['server']['total_timeout']:
        logging.error("Interaction with server took too long. Preempting")
        return

    dload_exps, del_exps = utils.compute_files_to_download(client_exps,
                                                           server_exps)

    # delete the files that aren't on the server
    for input_file in del_exps
        os.remove(os.path.join(config['dirs']['experiments_dir'], input_file))
    # get the files that have changed or we don't have
    for input_file in dload_exps:
        try:
            user.download_experiment(input_file)
        except Exception, e:
            logging.error("Unable to download experiment file %s", str(e))
        if time.time() - start > config['server']['total_timeout']:
            logging.error("Interaction with server took too long. Preempting")
            return

    # determine how to sync the input files
    client_inputs = utils.hash_folder(config['dirs']['data_dir'], '[!_]*.*'):
    try:
        server_inputs = user.input_files
    except Exception as exp:
        logging.error("Unable to retrive user inputs due to Exception: "
                      "%s. Preempting" % exp)
        return

    if time.time() - start > config['server']['total_timeout']:
        logging.error("Interaction with server took too long. Preempting")
        return

    dload_inputs, del_inputs = utils.compute_files_to_download(client_hashes,
                                                               server_hashes)

    # delete the files that aren't on the server
    for input_file in del_inputs:
        os.remove(os.path.join(config['dirs']['data_dir'], input_file))
    # get the files that have changed or we don't have
    for input_file in dload_inputs:
        try:
            user.download_input_file(input_file)
        except Exception, e:
            logging.error("Unable to download input file %s", str(e))
        if time.time() - start > config['server']['total_timeout']:
            logging.error("Interaction with server took too long. Preempting")
            return

    logging.info("Finished sync with %s", config['server']['server_url'])


def experiments_available(config):
    logging.info("Starting to check for experiments with %s",
                 config['server']['server_url'])

    try:
        user = User(config)
    except Exception, exp:
        logging.error("Unable to create user: %s" % str(exp))
        return False

    try:
        if user.experiments:
            return True
    except Exception, exp:
        logging.error("Unable to download experiment files: %s", str(exp))
    return False
