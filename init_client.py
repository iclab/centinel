#!/usr/bin/env python

import sys
import os
from os import path
from os.path import exists
from centinel.client import ServerConnection
from centinel.client_config import client_conf
from utils.colors import bcolors

c = client_conf()

print bcolors.OKBLUE + 'Initializing the client.' + bcolors.ENDC

def check_create_dir(path):
    if not os.path.exists(path):
        print "Creating directory in %s" % (path)
        os.makedirs(path)

check_create_dir(c.c['centinel_home_dir'])
check_create_dir(c.c['keys_dir'])
check_create_dir(c.c['confs_dir'])
check_create_dir(c.c['results_dir'])
check_create_dir(c.c['results_archive_dir'])
check_create_dir(c.c['logs_dir'])
check_create_dir(c.c['remote_experiments_dir'])
check_create_dir(c.c['custom_experiments_dir'])
check_create_dir(c.c['experiment_data_dir'])
check_create_dir(c.c['custom_experiment_data_dir'])

if len(sys.argv) > 1 and sys.argv[1] == "--offline":
    exit(0)

if c.config_read:
    print bcolors.FAIL + 'A configuration file already exists for %s, are you sure you want to initialize? (if so, type \'yes\') ' %(c.c['client_tag']) + bcolors.ENDC
    ans = raw_input()
    if ans.lower() <> "yes":
	print bcolors.OKBLUE + 'Nothing changed, exiting.' + bcolors.ENDC
	exit(0)

retry = True
while retry:
    try:
	print bcolors.OKBLUE + 'Connecting to server...' + bcolors.ENDC
	serverconn = ServerConnection()
	if not serverconn.connect(do_login = False):
	    raise Exception("Could not connect.")
	serverconn.initialize_client()
	retry = False
    except Exception as e:
	print bcolors.FAIL + "Error initializing: " + str(e) + bcolors.ENDC
	print bcolors.OKBLUE + "Want to retry? " + bcolors.ENDC
	ans = raw_input()
	if ans.lower() == "yes" or ans.lower() == "y" or ans.lower() == "Y":
	    print bcolors.OKBLUE + 'Retrying...' + bcolors.ENDC
	    retry = True
	else:
	    retry = False

serverconn.disconnect()
