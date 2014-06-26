import ConfigParser
import os
from utils.colors import bcolors

class client_conf:
    c  = {  'server_address' : "24.189.208.220",
	    'server_port' : "8082",
	    'centinel_homedir' : os.path.dirname(__file__),
	    'experiment_data_dir' : os.path.join(os.path.dirname(__file__), "experiment_data"),
	    'experiments_py_dir' : os.path.join(os.path.dirname(__file__), "py_experiments"),
	    'configurable_experiments_dir' : os.path.join(os.path.dirname(__file__), "conf_experiments"),
	    'results_dir' : os.path.join(os.path.dirname(__file__), "results"),
	    'client_keys_dir' : os.path.join(os.path.dirname(__file__), "client_keys"),
	    'results_archive_dir' : os.path.join(os.path.dirname(__file__), "results_archive"),
	    'config_file' : os.path.join(os.path.dirname(__file__), "confs/client_config.cfg"),
	    'server_public_rsa' : os.path.join(os.path.dirname(__file__), "client_keys/server_public_rsa.pem"),
	    'client_public_rsa' : os.path.join(os.path.dirname(__file__), "client_keys/client_public_rsa.pem"),
	    'client_private_rsa' : os.path.join(os.path.dirname(__file__), "client_keys/client_private_rsa.pem"),
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
	    print bcolors.FAIL + 'Error reading config file (did you run init.sh?).' + bcolors.ENDC
	    self.config_read = False
