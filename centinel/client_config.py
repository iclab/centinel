import sys
sys.path.append("../")
import ConfigParser
import os
from os.path import expanduser
from utils.colors import bcolors
from utils.logger import *

class client_conf:
    c  = {  'server_addresses' : "nrgairport.nrg.cs.stonybrook.edu 130.245.145.2",
	    'server_port' : "8082",
	    'centinel_home_dir' : os.path.join(expanduser("~"), ".centinel"),
	    'experiment_data_dir' : os.path.join(expanduser("~"), ".centinel/experiment_data"),
	    'custom_experiment_data_dir' : os.path.join(expanduser("~"), ".centinel/custom_experiment_data"),
	    'remote_experiments_dir' : os.path.join(expanduser("~"), ".centinel/remote_experiments"),
	    'custom_experiments_dir' : os.path.join(expanduser("~"), ".centinel/custom_experiments"),
	    'experiment_sync_delay' : "30",
	    'result_sync_delay' : "30",
	    'log_send_delay': "30",
	    'update_check_delay': "30",
	    'logs_dir' : os.path.join(expanduser("~"), ".centinel/logs"),
	    'results_dir' : os.path.join(expanduser("~"), ".centinel/results"),
	    'keys_dir' : os.path.join(expanduser("~"), ".centinel/keys"),
	    'confs_dir' : os.path.join(expanduser("~"), ".centinel/confs"),
	    'results_archive_dir' : os.path.join(expanduser("~"), ".centinel/results_archive"),
	    'config_file' : os.path.join(expanduser("~"), ".centinel/confs/client_config.cfg"),
	    'server_public_rsa' : os.path.join(expanduser("~"), ".centinel/keys/server_public_rsa.pem"),
	    'server_certificate' : os.path.join(expanduser("~"), ".centinel/keys/server_cert.pem"),
	    'client_public_rsa' : os.path.join(expanduser("~"), ".centinel/keys/client_public_rsa.pem"),
	    'client_private_rsa' : os.path.join(expanduser("~"), ".centinel/keys/client_private_rsa.pem"),
	    
	    'timeout' : "20",
	    'run_id' : "0",
	    'client_tag' : "unauthorized"}
    conf_file = ''
    def __init__(self):
	self.parser = ConfigParser.ConfigParser()
	self.parser.add_section('CentinelClient')
	try:
	    if not self.conf_file:
		self.conf_file = self.c['config_file']
	    for key, val in self.c.iteritems():
		self.parser.set('CentinelClient', key, val)
	    self.parser.read([self.conf_file,])
	    self.c.update(self.parser.items('CentinelClient'))
	    self.config_read = True
	    self.update()
	except ConfigParser.Error, message:
	    #log("w", 'Error reading config file (did you run init_client.py?).')
	    self.config_read = False

    def update(self):
	try:
	    of = open(self.conf_file, 'w')
	    self.parser.write(of)
	    of.close()
	except Exception as e:
	    log("e", "Error writing config file: " + str(e))

    def set(self, key, val):
	try:
	    self.parser.set('CentinelClient', key, val)
	except Exception as e:
	    log("e", "Error setting config value: " + str(e))

    def __getitem__(self, index):
	return self.parser.get('CentinelClient', index)