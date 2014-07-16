import sys
sys.path.append("../")
import ConfigParser
import os
from utils.colors import bcolors
from utils.logger import *

class client_conf:
    c  = {  'server_address' : "nrgairport.nrg.cs.stonybrook.edu",
	    'server_port' : "8082",
	    'centinel_homedir' : os.path.dirname(__file__),
	    'experiment_data_dir' : os.path.join(os.path.dirname(__file__), "experiment_data"),
	    'remote_experiments_dir' : os.path.join(os.path.dirname(__file__), "remote_experiments"),
	    'custom_experiments_dir' : os.path.join(os.path.dirname(__file__), "custom_experiments"),
	    'experiment_sync_delay' : "30",
	    'result_sync_delay' : "30",
	    'log_send_delay': "30",
	    'logs_dir' : os.path.join(os.path.dirname(__file__), "logs"),
	    'results_dir' : os.path.join(os.path.dirname(__file__), "results"),
	    'keys_dir' : os.path.join(os.path.dirname(__file__), "keys"),
	    'results_archive_dir' : os.path.join(os.path.dirname(__file__), "results_archive"),
	    'config_file' : os.path.join(os.path.dirname(__file__), "confs/client_config.cfg"),
	    'server_public_rsa' : os.path.join(os.path.dirname(__file__), "keys/server_public_rsa.pem"),
	    'client_public_rsa' : os.path.join(os.path.dirname(__file__), "keys/client_public_rsa.pem"),
	    'client_private_rsa' : os.path.join(os.path.dirname(__file__), "keys/client_private_rsa.pem"),
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
