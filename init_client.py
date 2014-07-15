#!/usr/bin/env python

import sys
import os
from os import path
from os.path import exists
from centinel.client import ServerConnection
from centinel.client_config import client_conf
from utils.colors import bcolors

selection = sys.argv
selection.pop(0)
c = client_conf()

print bcolors.OKBLUE + 'Initializing the client.' + bcolors.ENDC

def check_create_dir(path):
    if not os.path.exists(path):
        print "Creating directory in %s" % (path)
        os.makedirs(path)

check_create_dir(c.c['keys_dir'])
check_create_dir(c.c['results_dir'])
check_create_dir(c.c['results_archive_dir'])
check_create_dir(c.c['logs_dir'])
check_create_dir(c.c['remote_experiments_dir'])
check_create_dir(c.c['custom_experiments_dir'])


if c.config_read:
    print bcolors.FAIL + 'A configuration file already exists for %s, are you sure you want to initialize? (if so, type \'yes\') ' %(c.c['client_tag']) + bcolors.ENDC
    ans = raw_input()
    if ans.lower() <> "yes":
	print bcolors.OKBLUE + 'Nothing changed, exiting.' + bcolors.ENDC
	exit(0)


print bcolors.OKBLUE + 'Connecting to server...' + bcolors.ENDC
serverconn = ServerConnection()
if not serverconn.connect(do_login = False):
    exit(1)

serverconn.initialize_client()

serverconn.disconnect()
