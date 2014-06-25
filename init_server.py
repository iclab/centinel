#!/usr/bin/env python

import sys

from centinel.utils.colors import bcolors
from centinel.utils.rsacrypt import RSACrypt
from centinel.server_config import server_conf
from centinel.client_config import client_conf
selection = sys.argv
selection.pop(0)

sco = server_conf()
cco = client_conf()

print bcolors.OKBLUE + 'Creating new server keys.' + bcolors.ENDC
cr = RSACrypt()

try:
    open(sco.c['public_rsa_file'], "w").write(cr.public_key_string())
    open(cco.c['server_public_rsa'], "w").write(cr.public_key_string())
    open(sco.c['private_rsa_file'], "w").write(cr.private_key_string())
except:
    print bcolors.FAIL + "Error writing keys." + bcolors.ENDC
    exit(1)

print bcolors.OKGREEN + "Server keys created successfully." + bcolors.ENDC
print bcolors.OKBLUE + "Be sure to transfer the server public key to all clients: " + bcolors.ENDC
print cr.public_key_string()