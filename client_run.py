#!/usr/bin/env python

import sys
import os
import time
from centinel import experiment_runner
from centinel.client import ServerConnection
from utils.colors import bcolors
from utils.logger import *
from time import strftime
from datetime import datetime, timedelta
import logging
from centinel.client_config import client_conf

conf = client_conf()
last_checked_for_updates = ""
experiments_last_synced = ""
results_last_synced = ""
logs_last_sent = ""

class UpdateException(Exception):
    def __init__(self, message = ""):
	self.message = message

def die():
    raise (SystemExit)

def run_exp(selection):
    log("i", 'Starting the exepriments.')
    experiment_runner.run(selection)
    log("s", 'Experiments done.')

def update_check():
    global last_checked_for_updates
    log("i", 'Checking for updates...')
    if not serverconn.check_for_updates():
	last_checked_for_updates = datetime.now()
	log("i", "Already running the latest version.")
    else:
	raise UpdateException

def sync_res():
    global results_last_synced
    log("i", 'Starting results sync.')
    serverconn.sync_results()
    results_last_synced = datetime.now()

def sync_exp():
    global experiments_last_synced
    log("i", 'Starting experiment sync.')
    serverconn.sync_experiments()
    experiments_last_synced = datetime.now()

def send_logs():
    global logs_last_sent
    log("i", 'Sending logs.')
    serverconn.send_logs()
    logs_last_sent = datetime.now()

def centinel_run(args):
    if not os.path.exists(conf.c['logs_dir']):
        log("i", "Creating logs directory in %s." % (conf.c['logs_dir']))
	os.makedirs(conf.c['logs_dir'])

    logging.basicConfig(filename=os.path.join(conf.c['logs_dir'], strftime("%Y-%m-%d-%H:%M:%S")  + ".log"), level=logging.DEBUG)

    log("i", "Client daemon is running...")

    selection = args
    selection.pop(0)

    if selection:
	run_exp(selection)
	return 0

    print open("centinel_client_ascii_art", "r").read()

    global serverconn
    serverconn = ServerConnection()

    if not serverconn.connect():
	log("e", 'Server not connected.')

    while 1:
	try:
	    if not serverconn.logged_in:
		raise Exception("Not logged in.")

	    if not last_checked_for_updates or ((datetime.now() - last_checked_for_updates).seconds > int(conf.c['update_check_delay'])):
		update_check()

	    if not experiments_last_synced or ((datetime.now() - experiments_last_synced).seconds > int(conf.c['experiment_sync_delay'])):
		sync_exp()

	    if not results_last_synced or ((datetime.now() - results_last_synced).seconds > int(conf.c['result_sync_delay'])):
		sync_res()

	    if not logs_last_sent or ((datetime.now() - logs_last_sent).seconds > int(conf.c['log_send_delay'])):
		send_logs()


	    server_response = serverconn.beat()

	    if not server_response:
		serverconn.disconnect()
		raise Exception("No server response received.")

	    
	    elif server_response <> 'beat':
		log("i", "Executing commands... (" + server_response + ")")
		for command in server_response.split(";"):
	    	    try:
	    		command = command.strip()
			if command == '':
		    	    continue
			elif command == "sync_results" or command == "sync_res":
			    sync_res()
			elif command == "send_logs":
			    send_logs()
			elif command == "sync_experiments" or command == "sync_exp":
			    sync_exp()
			elif command.split()[0] == "run_exp" or command.split()[0] == "run":
			    run_exp(command.split()[1:])
			elif command == "die":
			    die()
			else:
			    log("e", "Command %s not recognized." %(command))
		    except Exception as e:
			log("e", "Command %s failed to execute: " %(command) + str(e))

	    time.sleep(5) # Sleep for heartbeat duration.
	except (KeyboardInterrupt, SystemExit):
	    log("w", "Shutdown requested, shutting centinel down...")
	    serverconn.disconnect()
	    # do some shutdown stuff, then close
	    return 0
	except UpdateException:
	    log("w", "Centinel update package received, shutting down to apply updates...")
	    return 2

	except Exception as e:
	    log("e", "An exception occured: " + str(e))
	    log("i", "Trying to recover...")
	    fixed = False
	    try:
		while not fixed:
    		    try:
			serverconn.disconnect()
			fixed = serverconn.connect() and serverconn.logged_in
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
		return 0
	    log("s", "We're back in business!")

    serverconn.disconnect()
