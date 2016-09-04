import getpass
import json
import logging
import os

import centinel


class Configuration:

    def __init__(self):

        self.params = {}

        # version info
        version_info = {'version': centinel.__version__}
        self.params['version'] = version_info

        # centinel user
        user_info = {'current_user': getpass.getuser()}
        user_home = os.path.expanduser('~' + user_info['current_user'])
        user_info['centinel_home'] = os.path.join(user_home, '.centinel')
        user_info['is_vpn'] = False
        self.params['user'] = user_info

        # directory structure
        # by default, *ALWAYS* use the directories in the home directory
        dirs = {
            'experiments_dir': os.path.join(self.params['user']['centinel_home'], 'experiments'),
            'data_dir': os.path.join(self.params['user']['centinel_home'], 'data'),
            'results_dir': os.path.join(self.params['user']['centinel_home'], 'results')
        }
        self.params['dirs'] = dirs

        # if we creating a new config file, then we can expect to be
        # setting up the the home directory, so we should create all
        # of these directories if they don't exist
        for dir_key in self.params['dirs']:
            directory = self.params['dirs'][dir_key]
            if not os.path.exists(directory):
                os.makedirs(directory)

        # results
        results = {'delete_after_sync': True,
                   'files_per_archive': 10,
                   'record_pcaps': True,
                   'upload_pcaps': True}
        self.params['results'] = results

        # logging
        self.params['log'] = {}
        self.params['log']['log_level'] = logging.INFO
        self.params['log']['log_file'] = os.path.join(self.params['user']['centinel_home'],
                                                      "centinel.log")
        self.params['log']['log_format'] = '%(asctime)s %(filename)s(line %(lineno)d) ' \
                                           '%(levelname)s: %(message)s'

        # experiments
        experiments = {'tcpdump_params': ["-i", "any"]}
        self.params['experiments'] = experiments

        # server
        servers = {'server_url': "https://server.iclab.cs.stonybrook.edu:8082",
                   'login_file': os.path.join(self.params['user']['centinel_home'], 'login'),
                   # the entire transaction should take less than 30 min
                   'total_timeout': 60*30,
                   # set a socket timeout of 15 seconds (no way to do per request
                   # platform independently)
                   'req_timeout': 15,
                   'verify': True}
        self.params['server'] = servers

        # proxy
        proxy = {'proxy_type': None,    # "socks" or "http"
                 'proxy_url': None,     # "http://127.0.0.1:9050"
                 'proxy': None}
        # TODO: this if clause looks useless to me (Adrian)
        if proxy['proxy_type']:
            proxy['proxy'] = {proxy['proxy_type']: proxy['proxy_url']}
        self.params['proxy'] = proxy

    def parse_config(self, config_file):
        """
        Given a configuration file, read in and interpret the results

        :param config_file:
        :return:
        """

        with open(config_file, 'r') as f:
            config = json.load(f)
        self.params = config
        if self.params['proxy']['proxy_type']:
            self.params['proxy'] = {self.params['proxy']['proxy_type']:
                                    self.params['proxy']['proxy_url']}

    def update(self, old, backup_path=None):
        """
        Update the old configuration file with new values.

        :param old: old configuration to update.
        :param backup_path: path to write a backup of the old config file.

        :return:
        """
        for category in old.params.keys():
            for parameter in old.params[category].keys():
                if (category in self.params and parameter in self.params[category] and
                        (old.params[category][parameter] != self.params[category][parameter]) and
                        (category != "version")):
                    print ("Config value '%s.%s' "
                           "in old configuration is different "
                           "from the new version\n"
                           "[old value] = %s\n"
                           "[new value] = %s"
                           "" % (category, parameter,
                                 old.params[category][parameter],
                                 self.params[category][parameter]))
                    answer = raw_input("Do you want to overwrite? ([y]/n) ")
                    while answer.lower() not in ['y', 'yes', 'n', 'no']:
                        answer = raw_input("Answer not recongnized. Enter 'y' or 'n'. ")

                    if answer in ['n', 'no']:
                        old_value = old.params[category][parameter]
                        self.params[category][parameter] = old_value
                elif not (category in self.params and
                          parameter in self.params[category]):
                    print ("Deprecated config option '%s.%s' has "
                           "been removed." % (category, parameter))
        if backup_path is not None:
            old.write_out_config(backup_path)
            print "Backup saved in %s." % backup_path

    def write_out_config(self, config_file):
        """
        Write out the configuration file

        :param config_file:
        :return:

        Note: this will erase all comments from the config file

        """
        with open(config_file, 'w') as f:
            json.dump(self.params, f, indent=2,
                      separators=(',', ': '))
