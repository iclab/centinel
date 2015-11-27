import getpass
import json
import logging
import os

import centinel

class Configuration():

    def __init__(self,):

        self.params = {}

        # version info
        version_info = {}
        version_info['version'] = centinel.__version__
        self.params['version'] = version_info

        # centinel user
        user_info = {}
        user_info['current_user']  = getpass.getuser()
        user_home          = os.path.expanduser('~' + user_info['current_user'])
        user_info['centinel_home'] = os.path.join(user_home, '.centinel')
        user_info['is_vpn'] = False
        self.params['user'] = user_info

        # directory structure
        dirs = {}
        # by default, *ALWAYS* use the directories in the home directory
        dirs['experiments_dir'] = os.path.join(self.params['user']['centinel_home'],
                                               "experiments")
        dirs['data_dir']        = os.path.join(self.params['user']['centinel_home'],
                                               "data")
        dirs['results_dir']     = os.path.join(self.params['user']['centinel_home'],
                                               'results')
        self.params['dirs'] = dirs

        # if we creating a new config file, then we can expect to be
        # setting up the the home directory, so we should create all
        # of these directories if they don't exist
        for dir_key in self.params['dirs']:
            directory = self.params['dirs'][dir_key]
            if not os.path.exists(directory):
                os.makedirs(directory)

        # results
        results = {}
        results['delete_after_sync'] = True
        results['files_per_archive'] = 10
        results['record_pcaps'] = True
        results['upload_pcaps'] = True
        self.params['results'] = results

        # logging
        self.params['log'] = {}
        self.params['log']['log_level'] = logging.INFO
        self.params['log']['log_file'] = os.path.join(self.params['user']['centinel_home'],
                                                      "centinel.log")
        self.params['log']['log_format'] = ('%(asctime)s '
            '%(filename)s(line %(lineno)d) %(levelname)s: %(message)s')

        # experiments
        experiments = {}
        experiments['tcpdump_params'] = ["-i", "any"]
        self.params['experiments'] = experiments

        # server
        servers = {}
        servers['server_url'] = "https://server.iclab.org:8082"
        servers['login_file'] = os.path.join(self.params['user']['centinel_home'],
                                             'login')
        # the entire transaction should take less than 5 min
        servers['total_timeout'] = 60*5
        # set a socket timeout of 15 seconds (no way to do per request
        # platform independently)
        servers['req_timeout'] = 15
        servers['verify'] = True
        self.params['server'] = servers

        # proxy
        proxy = {}
        proxy['proxy_type'] = None  # "socks" or "http"
        proxy['proxy_url']  = None  # "http://127.0.0.1:9050"
        proxy['proxy'] = None
        if proxy['proxy_type']:
            proxy['proxy']  = {proxy['proxy_type']: proxy['proxy_url']}
        self.params['proxy'] = proxy

    def parse_config(self, config_file):
        """Given a configuration file, read in and interpret the results"""

        with open(config_file, 'r') as f:
            config = json.load(f)
        self.params = config
        if self.params['proxy']['proxy_type']:
            self.params['proxy']  = {self.params['proxy']['proxy_type']:
                                     self.params['proxy']['proxy_url']}

    def write_out_config(self, config_file):
        """Write out the configuration file

        Note: this will erase all comments from the config file

        """
        with open(config_file, 'w') as f:
            json.dump(self.params, f, indent = 2,
                      separators=(',', ': '))
