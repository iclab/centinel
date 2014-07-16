import sys
sys.path.append("../")
import ConfigParser
import os
from utils.colors import bcolors

class server_conf:
    c  = {  'server_port' : "8082",
	    'centinel_homedir' : os.path.dirname(__file__),
	    'experiments_dir' : os.path.join(os.path.dirname(__file__), "server_experiments"),
	    'experiment_data_dir' : os.path.join(os.path.dirname(__file__), "server_experiments_data"),
	    'results_dir' : os.path.join(os.path.dirname(__file__), "server_results"),
	    'log_archive_dir' : os.path.join(os.path.dirname(__file__), "log_archive"),
	    'config_file' : os.path.join(os.path.dirname(__file__), "confs/server_config.cfg"),
	    'client_keys_dir' : os.path.join(os.path.dirname(__file__), "server_keys/clients/"),
	    'server_keys_dir' : os.path.join(os.path.dirname(__file__), "server_keys/"),
	    'public_rsa_file' : os.path.join(os.path.dirname(__file__), "server_keys/server_public_rsa.pem"),
	    'private_rsa_file' : os.path.join(os.path.dirname(__file__), "server_keys/server_private_rsa.pem")}

    def __init__(self,conf_file = ''):
	parser = ConfigParser.ConfigParser()
	try:
	    if not conf_file:
		conf_file = self.c['config_file']
	    parser.read([conf_file,])
	    self.c.update(parser.items('CentinelServer'))
	except ConfigParser.Error, message:
	    print bcolors.WARNING + 'Error reading server config file! Using defaults...' + bcolors.ENDC
