#!/usr/bin/env python

import sys
import os
import time
from centinel import experiment_runner
from centinel.client import ServerConnection
from utils.colors import bcolors
from utils.logger import *
from time import strftime
import logging
from centinel.client_config import client_conf

conf = client_conf()

def run_exp(selection):
    log("i", 'Starting the exepriments.')
    experiment_runner.run(selection)
    log("s", 'Experiments done.')


def sync_res():
    log("i", 'Starting results sync.')
    serverconn.sync_results()

def sync_exp():
    log("i", 'Starting experiments sync.')
    serverconn.sync_experiments()

if not os.path.exists(conf.c['logs_dir']):
    log("i", "Creating logs directory in %s." % (conf.c['logs_dir']))
    os.makedirs(conf.c['logs_dir'])

logging.basicConfig(filename=os.path.join(conf.c['logs_dir'], strftime("%Y-%m-%d-%H:%M:%S")  + ".log"), level=logging.DEBUG)

log("i", "Client daemon is running...")

selection = sys.argv
selection.pop(0)

if selection:
    run_exp(selection)
    exit(0)

print open("centinel_client_ascii_art", "r").read()

serverconn = ServerConnection()

if not serverconn.connect():
    log("e", 'Server not connected.')

while 1:
    try:
	server_response = serverconn.beat()

	if not server_response:
	    serverconn.disconnect()
	    raise(Exception)

	    
	elif server_response <> 'beat':
	    log("i", "Executing commands... (" + server_response + ")")
	    for command in server_response.split(";"):
	        try:
	    	    command = command.strip()
		    if command == '':
		        continue
		    elif command == "sync_results" or command == "sync_res":
			sync_res()
		    elif command == "sync_experiments" or command == "sync_exp":
			sync_exp()
		    elif command.split()[0] == "run_exp" or command.split()[0] == "run":
			run_exp(command.split()[1:])
		    else:
			log("e", "Command %s not recognized." %(command))
		except Exception as e:
		    log("e", "Command %s failed to execute: " %(command) + str(e))
	serverconn.sync_experiments()
	time.sleep(5) # Sleep for heartbeat duration.
    except (KeyboardInterrupt, SystemExit):
	log("w", "Shutdown requested, shutting centinel down...")
	serverconn.disconnect()
	# do some shutdown stuff, then close
	exit(0)
    except Exception as e:
	log("e", "An exception occured: " + str(e))
	log("i", "Trying to recover...")
	fixed = False
	try:
	    while not fixed:
    		try:
		    serverconn.disconnect()
		    fixed = serverconn.connect()
		    if fixed:
			break
		except Exception as e:
		    log("e", "An exception occured when trying to recover: " + str(e))
		    log("i", "Rerying...")
		time.sleep(5) # Sleep before retrying
		fixed = False
	except (KeyboardInterrupt, SystemExit):
	    log("w", "Shutdown requested, shutting centinel down...")
	    # do some shutdown stuff, then close
	    serverconn.disconnect()
	    exit(0)
	log("s", "We're back in business!")

serverconn.disconnect()