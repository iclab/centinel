import ConfigParser
import os
from utils.colors import bcolors

class conf:
    c  = {  'server_address' : "localhost",
	    'server_port' : "8082",
	    'centinel_homedir' : os.path.dirname(__file__),
	    'data_dir' : os.path.join(os.path.dirname(__file__), "data"),
	    'experiments_dir' : os.path.join(os.path.dirname(__file__), "experiments"),
	    'results_dir' : os.path.join(os.path.dirname(__file__), "results"),
	    'results_archive_dir' : os.path.join(os.path.dirname(__file__), "results_archive"),
	    'server_results_dir' : os.path.join(os.path.dirname(__file__), "server_results"),
	    'server_public_rsa' : "server_public_rsa.pem",
	    'client_public_rsa' : "client_public_rsa.pem",
	    'server_private_rsa' : "server_private_rsa.pem",
	    'client_private_rsa' : "client_private_rsa.pem",
	    'client_tag' : "sample_client"}

    def __init__(self,conf_file = 'config.cfg'):
	parser = ConfigParser.ConfigParser()
	try:
	    parser.read([conf_file,])
	    self.c.update(parser.items('CentinelConfig'))
	except ConfigParser.Error, message:
	    print bcolors.FAIL + 'Error reading config file (did you run init.sh?).' + bcolors.ENDC
