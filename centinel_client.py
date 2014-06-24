#!/usr/bin/env python

import sys

from centinel import experiment_runner
from centinel.serverconnection import ServerConnection
from centinel.utils.colors import bcolors

selection = sys.argv
selection.pop(0)

print bcolors.OKBLUE + 'Starting the exepriments.' + bcolors.ENDC
experiment_runner.run(selection)
print bcolors.OKGREEN + 'Experiments done.' + bcolors.ENDC


print bcolors.OKBLUE + 'Starting the exepriments.' + bcolors.ENDC
serverconn = ServerConnection()
if not serverconn.connect():
    print bcolors.FAIL + 'Results not submitted.' + bcolors.ENDC
    exit(1)

serverconn.sync_results()

serverconn.disconnect()