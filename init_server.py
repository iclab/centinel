#!/usr/bin/env python

import sys
import os
from os import path
from os.path import exists
from utils.colors import bcolors
from utils.rsacrypt import RSACrypt
from sirocco.server_config import server_conf

selection = sys.argv
selection.pop(0)

sco = server_conf()

def check_create_dir(path):
    if not os.path.exists(path):
        print "Creating directory in %s" % (path)
        os.makedirs(path)

print bcolors.OKBLUE + 'Creating new server keys...' + bcolors.ENDC
cr = RSACrypt()

try:
    check_create_dir(sco.c['server_keys_dir'])
    check_create_dir(sco.c['client_keys_dir'])
    check_create_dir(sco.c['log_archive_dir'])
    check_create_dir(sco.c['results_dir'])

    open(sco.c['public_rsa_file'], "w").write(cr.public_key_string())
    open(sco.c['private_rsa_file'], "w").write(cr.private_key_string())
except:
    print bcolors.FAIL + "Error writing keys." + bcolors.ENDC
    exit(1)

print bcolors.OKGREEN + "Server keys created successfully." + bcolors.ENDC
print cr.public_key_string()