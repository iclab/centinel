import os
import glob
import uuid
import json
import requests
import logging

import config

class User:
    def __init__(self):
        # check for login file
        if os.path.isfile(config.login_file):
            with open(config.login_file) as login_fh:
                login_details = json.load(login_fh)
                self.username = login_details.get('username')
                self.password = login_details.get('password')
                self.auth     = (self.username, self.password)
        else:
            user.create_user()

    def request(self, slug):
        url = "%s/%s" % (config.server_url, slug)
        req = requests.get(url, auth=self.auth)
        req.raise_for_status()

        return req.json()

    @property
    def recommended_version(self):
        return int(self.request("version")["version"])

    @property
    def experiments(self):
        return self.request("experiments")["experiments"]

    @property
    def results(self):
        return self.request("results")

    @property
    def clients(self):
        return self.request("clients")

    def submit_result(self, file_name):
        logging.info("Uploading result file - %s", file_name)

        with open(file_name) as result_file:
            file = {'result' : result_file}
            url  = "%s/%s" % (config.server_url, "results")
            req  = requests.post(url, files=file,
                                 proxies=config.proxy, auth=self.auth)

        req.raise_for_status()

    def download_experiment(self, name):
        logging.info("Downloading experiment - %s", name)

        url = "%s/%s/%s" % (config.server_url, "experiments", name)
        req = requests.get(url, proxies=config.proxy, auth=self.auth)
        req.raise_for_status()

        name = "%s.py" % name
        with open(os.path.join(config.experiments_dir, name), "w") as exp_fh:
            exp_fh.write(req.content)

    def register(self, username, password):
        logging.info("Registering new user %s" % (username))

        url     = "%s/%s" % (config.server_url, "register")
        payload = {'username': username, 'password': password}
        headers = {'content-type': 'application/json'}
        req     = requests.post(url, data=json.dumps(payload), headers=headers)

        req.raise_for_status()

    def create_user(self):
        self.username = str(uuid.uuid4())
        self.password = os.urandom(64).encode('base-64')
        self.auth     = (self.username, self.password)

        try:
            self.register(self.username, self.password)
            with open(config.login_file, "w") as login_fh:
                login_details = {'username': self.username,
                                 'password': self.password}
                json.dump(login_details, login_fh)
        except Exception, e:
            logging.error("Unable to register: %s" % str(e))


def sync():
    logging.info("Starting sync with %s", config.server_url)
    user = User()

    # send all results
    # XXX: delete all files after sync?
    for path in glob.glob(os.path.join(config.results_dir,'[!_]*.json')):
        try:
            submit_result(path)
        except Exception, e:
            logging.error("Unable to send result file: %s" % str(e))

    # get all experiment names
    available_experiments = []
    for path in glob.glob(os.path.join(config.experiments_dir,'[!_]*.py')):
        file_name, _ = os.path.splitext(os.path.basename(path))
        available_experiments.append(file_name)
    available_experiments = set(available_experiments)

    # download new experiments from server
    try:
        map(user.download_experiment,
            set(user.experiments) - available_experiments)
    except Exception, e:
        logging.error("Unable to download experiment files %s", str(e))

    logging.info("Finished sync with %s", config.server_url)
