import logging
import time
from time import strftime
from colors import bcolors

def _log(log_type, message, to_screen=True):
    """
    log_type:
	e = error	(red when printed)
	w = warning	(yellow when printed)
	i = info	(blue when printed)
	s = success 	(same as info, but it's green when printed)

    to_screen:
	True		log message will be also printed to standard output
	False		log message will only be written to log file
    """

    message = strftime("%Y-%m-%d %H:%M:%S") + " " + message
    color = ""
    if log_type == "e":
	color = bcolors.FAIL
	logging.error("\t" + message)
    elif log_type == "w":
	color = bcolors.WARNING
	logging.warning("\t" + message)
    elif log_type == "i":
	color = bcolors.OKBLUE
	logging.info("\t" + message)
    elif log_type == "s":
	color = bcolors.OKGREEN
	logging.info("\t" + message)
    else:
	raise Exception("Log message type not recognized.")
    
    if to_screen:
	print color + message + bcolors.ENDC

def log(log_type, message, address=False, tag=""):
    if tag:
	message ="(" + tag + ") " + message
    if address:
	message = address[0] + ":" + str(address[1]) + " " + message
    _log(log_type, message)