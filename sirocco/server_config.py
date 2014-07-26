import sys
sys.path.append("../")
import ConfigParser
import os
from utils.colors import bcolors

class server_conf:
    c  = {  'server_port' : "8082",
	    'kobra_port' : "8083",
	    'centinel_homedir' : os.path.dirname(__file__),
	    'kobra_users_file' : os.path.join(os.path.dirname(__file__), "kobra_users_list"),
	    'experiments_dir' : os.path.join(os.path.dirname(__file__), "server_experiments"),
	    'experiment_data_dir' : os.path.join(os.path.dirname(__file__), "server_experiments_data"),
	    'results_dir' : os.path.join(os.path.dirname(__file__), "server_results"),
	    'log_archive_dir' : os.path.join(os.path.dirname(__file__), "log_archive"),
	    'config_file' : os.path.join(os.path.dirname(__file__), "confs/server_config.cfg"),
	    'client_keys_dir' : os.path.join(os.path.dirname(__file__), "server_keys/clients/"),
	    'pack_maker_path' : os.path.join(os.path.dirname(__file__), "../make_update.sh"),
	    'server_keys_dir' : os.path.join(os.path.dirname(__file__), "server_keys/"),
	    'public_rsa_file' : os.path.join(os.path.dirname(__file__), "server_keys/server_public_rsa.pem"),
	    'private_rsa_file' : os.path.join(os.path.dirname(__file__), "server_keys/server_private_rsa.pem")}
    conf_file = ""
    def __init__(self):
	self.parser = ConfigParser.ConfigParser()
	try:
	    if not self.conf_file:
		self.conf_file = self.c['config_file']
	    self.parser.read([self.conf_file,])
	    self.c.update(parser.items('CentinelServer'))
	    self.update()
	except ConfigParser.Error, message:
	    #log("w", 'Error reading config file (did you run init_client.py?).')
	    self.config_read = False

    def update(self):
	try:
	    for key, val in self.c.iteritems():
		self.parser.set('CentinelClient', key, val)
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
