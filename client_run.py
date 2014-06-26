#!/usr/bin/env python

import sys
import time
from centinel import experiment_runner
from centinel.serverconnection import ServerConnection
from centinel.utils.colors import bcolors

selection = sys.argv
selection.pop(0)


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

print bcolors.HEADER + "Client daemon is running..." + bcolors.ENDC

serverconn = ServerConnection()
if not serverconn.connect():
    print bcolors.FAIL + 'Server not connected.' + bcolors.ENDC

while 1:
    try:
	
	if not serverconn.connected:
    	    raise Exception
	server_response = serverconn.beat()

	if not server_response:
	    print bcolors.FAIL + "Server didn't beat!" + bcolors.ENDC
	    serverconn.disconnect()
	    exit;
	elif server_response <> 'beat':
	    print bcolors.HEADER + "Executing commands... (" + server_response + ")" + bcolors.ENDC
	    for command in server_response.split(";"):
	        try:
	    	    command = command.strip()
		    if command == '':
		        continue
		    elif command == "sync_results" or command == "sync":
			sync()
		    elif command == "fetch_exp" or command == "fetch":
			fetch()
		    elif command.split()[0] == "run_exp" or command.split()[0] == "run":
			run_exp(command.split()[1:])
		    else:
			print bcolors.FAIL + "Command %s not recognized." %(command) + bcolors.ENDC
		except:
		    print bcolors.FAIL + "Command %s failed to execute." %(command) + bcolors.ENDC
	time.sleep(5) # Sleep for heartbeat duration.
    except (KeyboardInterrupt, SystemExit):
	print bcolors.WARNING + "Shutdown requested, shutting server down..." + bcolors.ENDC
	serverconn.disconnect()
	# do some shutdown stuff, then close
	exit(0)
    except:
	print bcolors.FAIL + "An exception occured at heartbeat." + bcolors.ENDC
	print bcolors.OKBLUE + "Trying to recover..." + bcolors.ENDC
	fixed = False
	try:
	    while not fixed:
    		try:
		    serverconn.disconnect()
		    serverconn = ServerConnection()
		    serverconn.connect()
		    if not serverconn.connected:
			raise Exception
		    fixed = True
		except:
		    print bcolors.FAIL + "Error persists. Rerying..." + bcolors.ENDC
		    time.sleep(5) # Sleep before retrying
		    fixed = False
	    print bcolors.OKGREEN + "We're back business!" + bcolors.ENDC
	except (KeyboardInterrupt, SystemExit):
	    print bcolors.WARNING + "Shutdown requested, shutting server down..." + bcolors.ENDC
	    # do some shutdown stuff, then close
	    exit(0)


    

serverconn.disconnect()