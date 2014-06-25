#!/usr/bin/env python

import sys
import os
from os import path
from os.path import exists


from centinel.serverconnection import ServerConnection
from centinel.utils.colors import bcolors
from centinel.client_config import client_conf

selection = sys.argv
selection.pop(0)
c = client_conf()

def check_create_dir(path):
    if not os.path.exists(path):
        print "Creating directory in %s" % (path)
        os.makedirs(path)

check_create_dir(c.c['client_keys_dir'])

print bcolors.OKBLUE + 'Initializing the client.' + bcolors.ENDC
if c.config_read:
    print bcolors.FAIL + 'A configuration file already exists for %s, are you sure you want to initialize? (if so, type \'yes\') ' %(c.c['client_tag']) + bcolors.ENDC
    ans = raw_input()
    if ans.lower() <> "yes":
	print bcolors.OKBLUE + 'Nothing changed, exiting.' + bcolors.ENDC
	exit(0)


print bcolors.OKBLUE + 'Connecting to server...' + bcolors.ENDC
serverconn = ServerConnection()
if not serverconn.connect():
    exit(1)

serverconn.initialize_client()

serverconn.disconnect()
