#!/usr/bin/env python

import sys

from centinel.serverconnection import ServerConnection
from centinel.utils.colors import bcolors
from centinel.client_config import conf

selection = sys.argv
selection.pop(0)
c = conf()

print bcolors.OKBLUE + 'Starting the exepriments.' + bcolors.ENDC
if c.config_read:
    print bcolors.WARNING + 'A configuration file already exists for %s, are you sure you want to initialize? (if so, type \'yes\') ' + bcolors.ENDC
    ans = raw_input()
    if ans.lower() <> "yes":
	print bcolors.OKBLUE + 'Nothing changed, exiting.' + bcolors.ENDC
	exit(0)


print bcolors.OKBLUE + 'Starting sync.' + bcolors.ENDC
serverconn = ServerConnection()
if not serverconn.connect():
    exit(1)

#serverconn.sync_results()

serverconn.disconnect()
