import sys
sys.path.append("../")
import ConfigParser
import os
from os.path import expanduser
from utils.colors import bcolors
from utils.logger import *

class client_conf:
    c  = {  'server_address' : "nrgairport.nrg.cs.stonybrook.edu",
	    'server_port' : "8082",
	    'centinel_home_dir' : os.path.join(expanduser("~"), ".centinel"),
	    'experiment_data_dir' : os.path.join(expanduser("~"), ".centinel/experiment_data"),
	    'remote_experiments_dir' : os.path.join(expanduser("~"), ".centinel/remote_experiments"),
	    'custom_experiments_dir' : os.path.join(expanduser("~"), ".centinel/custom_experiments"),
	    'experiment_sync_delay' : "30",
	    'result_sync_delay' : "30",
	    'log_send_delay': "30",
	    'update_check_delay': "30",
	    'logs_dir' : os.path.join(expanduser("~"), ".centinel/logs"),
	    'results_dir' : os.path.join(expanduser("~"), ".centinel/results"),
	    'keys_dir' : os.path.join(expanduser("~"), ".centinel/keys"),
	    'confs_dir' : os.path.join(expanduser("~"), ".centinel/keys"),
	    'results_archive_dir' : os.path.join(expanduser("~"), ".centinel/results_archive"),
	    'config_file' : os.path.join(expanduser("~"), ".centinel/confs/client_config.cfg"),
	    'server_public_rsa' : os.path.join(expanduser("~"), ".centinel/keys/server_public_rsa.pem"),
	    'client_public_rsa' : os.path.join(expanduser("~"), ".centinel/keys/client_public_rsa.pem"),
	    'client_private_rsa' : os.path.join(expanduser("~"), ".centinel/keys/client_private_rsa.pem"),
	    'timeout' : 20,
	    'client_tag' : "unauthorized"}

    def __init__(self,conf_file = '' ):
	parser = ConfigParser.ConfigParser()
	try:
	    if not conf_file:
		conf_file = self.c['config_file']
	    parser.read([conf_file,])
	    self.c.update(parser.items('CentinelClient'))
	    self.config_read = True
	except ConfigParser.Error, message:
	    log("w", 'Error reading config file (did you run init_client.py?).')
	    self.config_read = False
