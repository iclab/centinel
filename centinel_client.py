#!/usr/bin/env python

import sys
import time
from centinel import experiment_runner
from centinel.serverconnection import ServerConnection
from centinel.utils.colors import bcolors

selection = sys.argv
selection.pop(0)


serverconn = ServerConnection()
if not serverconn.connect():
    print bcolors.FAIL + 'Server not connected.' + bcolors.ENDC
    exit(1)

def run_exp(selection):
    print bcolors.OKBLUE + 'Starting the exepriments.' + bcolors.ENDC
    experiment_runner.run(selection)
    print bcolors.OKGREEN + 'Experiments done.' + bcolors.ENDC


def sync():
    print bcolors.OKBLUE + 'Starting sync.' + bcolors.ENDC
    serverconn.sync_results()

def fetch():
    print bcolors.OKBLUE + 'Starting fetch.' + bcolors.ENDC
    # TODO:
    # Write results fetch.

while 1:
    server_response = serverconn.beat()
    if not server_response:
	print bcolors.FAIL + "Server didn't beat!" + bcolors.ENDC
	serverconn.disconnect()
	exit;
    elif server_response <> 'beat':
	print bcolors.HEADER + "Executing commands... (" + server_response + ")" + bcolors.ENDC
	for command in server_response.split(";"):
	    command = command.strip()
	    if command == '':
		continue
	    elif command == "sync_results" or command == "sync":
		sync()
		continue
	    elif command == "fetch_exp" or command == "fetch":
		fetch()
	    elif command.split()[0] == "run_exp" or command.split()[0] == "run":
		run_exp(command.split()[1:])
	    else:
		print bcolors.FAIL + "Command %s not recognized." %(command) + bcolors.ENDC

    time.sleep(5) # Sleep for heartbeat duration.
    

serverconn.disconnect()
