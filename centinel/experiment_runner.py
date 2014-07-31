import sys
sys.path.append("../")
import os
import json
import glob
import imp
import getpass
from test_primitives.http import ConfigurableHTTPRequestExperiment
from test_primitives.tcp_connect import ConfigurableTCPConnectExperiment
from test_primitives.ping	import ConfigurablePingExperiment
from test_primitives.dns_exp	import ConfigurableDNSExperiment
from test_primitives.traceroute	import ConfigurableTracerouteExperiment
from utils.logger import *
from utils.onlineapis import getmyip, geolocate, getESTTime
from datetime import datetime

from experiment import Experiment, ExperimentList
from client_config import client_conf

conf = client_conf()

EXPERIMENTS_DIR = conf['remote_experiments_dir']
EXPERIMENT_DATA_DIR = conf['experiment_data_dir']
CUSTOM_EXP_DIR = conf['custom_experiments_dir']
CUSTOM_EXP_DATA_DIR = conf['custom_experiment_data_dir']
RESULTS_DIR = conf['results_dir']

def get_results_dir():
    return RESULTS_DIR

def get_result_file(results_dir, exp_name, run_id):
    result_file = "%s-%s-%s.json" % (exp_name, run_id, datetime.now().isoformat())
    return os.path.join(results_dir, result_file)

def get_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return os.path.join(EXPERIMENT_DATA_DIR, input_file)

def get_custom_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return os.path.join(CUSTOM_EXP_DATA_DIR, input_file)

def get_custom_conf_input_file(experiment_name):
    input_file = "%s.cfg" % (experiment_name)
    return os.path.join(EXPERIMENTS_DIR, input_file)

def get_conf_input_file(experiment_name):
    input_file = "%s.cfg" % (experiment_name)
    return os.path.join(CUSTOM_EXP_DIR, input_file)

def load_experiments():
    # look for Python experiments in experiments directory
    for path in glob.glob(os.path.join(EXPERIMENTS_DIR,'[!_]*.py')):
        # get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        # load the experiment
        imp.load_source(name, path)

    # look for Python experiments in custom experiments directory
    for path in glob.glob(os.path.join(CUSTOM_EXP_DIR,'[!_]*.py')):
        # get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        # load the experiment
        imp.load_source(name, path)

    # return dict of experiment names and classes
    return ExperimentList.experiments

def load_conf_experiments():
    exp_list = []
    # look for configurable experiments in experiments directory
    for path in glob.glob(os.path.join(EXPERIMENTS_DIR,'[!_]*.cfg')):
        # get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        exp_list.append(name)

    # look for configurable experiments in custom experiments directory
    for path in glob.glob(os.path.join(CUSTOM_EXP_DIR, '[!_]*.cfg')):
	# get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        exp_list.append(name)
    # return dict of experiment names and classes

    return exp_list
    

def run(selection = [], operator = "centinel"):
    results_dir = get_results_dir()    

    if not selection:
	log("i", "No experiments specified, running all...")
	run_all = True
    else:
	run_all = False

    if not os.path.exists(results_dir):
        log("i", "Creating results directory in %s." % (results_dir))
        os.makedirs(results_dir)

    experiments = load_experiments()
    conf_experiments = load_conf_experiments()

    if run_all:
        for name, Exp in experiments.items():
	    results,run_id = prep_results(operator, name)
	    result_file = get_result_file(results_dir, name, run_id)
	    result_file = open(result_file, "w")
	    results[name] = execute_experiment(name, Exp, run_id)
	    json.dump(results, result_file)
	    result_file.close()

	for name in conf_experiments:
	    result_file = get_result_file(results_dir, name)
	    result_file = open(result_file, "w")
	    results,run_id = prep_results(operator, name)
	    results[name] = execute_conf_experiment(name, run_id)
	    json.dump(results, result_file)
	    result_file.close()
    else:
	ran = []
        for name in selection:
	    if not name in experiments.keys():
		continue
	    Exp = experiments[name]
	    results,run_id = prep_results(operator, name)
	    result_file = get_result_file(results_dir, name, run_id)
	    result_file = open(result_file, "w")
	    results[name] = execute_experiment(name, Exp, run_id)
	    ran.append(name);
	    json.dump(results, result_file)
	    result_file.close()
	
	for name in selection:
	    if not name in conf_experiments:
		continue
	    results,run_id = prep_results(operator, name)
	    http_results, dns_results, ping_results, tcp_results, traceroute_results = execute_conf_experiment(name, run_id)
	    result_file = get_result_file(results_dir, name, run_id)
	    result_file = open(result_file, "w")
	    if http_results:
		results["std_http"] = http_results
	    if dns_results:
		results["std_dns"] = dns_results
	    if tcp_results:
		results["std_tcp"] = tcp_results
	    if ping_results:
		results["std_ping"] = ping_results
	    if traceroute_results:
		results["std_traceroute"] = traceroute_results
	    ran.append(name)
	    json.dump(results, result_file)
	    result_file.close()


    for name in selection:
	if name not in ran:
	    log("e", "Experiment %s not found." %(name))



    log("s", "Finished running all experiments.")

def execute_experiment(name, Exp, run_id):
    results = {}
    input_file = get_input_file(name)
    if not os.path.isfile(input_file):
	input_file = get_custom_input_file(name)

    if not os.path.isfile(input_file):
	log("e", "No input file found for \"%s\". Skipping test." % (name))
	return
    
    log("i", "Reading input from \"%s\"" % (input_file))
    input_file = open(input_file)

    try:
    	log("w", "Running \"%s\" (run ID: %s) test.: %s" % (name, run_id))
    	exp = Exp(input_file)
    	exp.run()
    except Exception as e:
    	log("e", "Error running \"%s\" (run ID: %s): " %(name, run_id) + str(e))

    input_file.close()
    return exp.results

def execute_conf_experiment(name, run_id):
    results = {}
    input_file = get_conf_input_file(name)
    if not os.path.isfile(input_file):
	input_file = get_custom_conf_input_file(name)

    if not os.path.isfile(input_file):
	log ("e", "No input file found for \"%s\" (run ID: %s). Skipping test." % (name, run_id))
	return
    
    log ("i", "Reading config experiment from \"%s\"" % (input_file))

    log("w", "Running \"%s\" (run ID: %s) test." % (name, run_id))

    http_results = dns_results = ping_results = tcp_results = traceroute_results = ""
    try:
    	exp = ConfigurableHTTPRequestExperiment(input_file)
    	exp.run()
	http_results = exp.results
    except Exception as e:
    	log("e", "Error running HTTP test: " + str(e))

    try:
	exp = ConfigurableDNSExperiment(input_file)
    	exp.run()
	dns_results = exp.results
    except Exception as e:
    	log("e", "Error running DNS test: " + str(e))

    try:
	exp = ConfigurablePingExperiment(input_file)
    	exp.run()
	ping_results = exp.results
    except Exception as e:
    	log("e", "Error running ping test: " + str(e))

    try:
	exp = ConfigurableTCPConnectExperiment(input_file)
    	exp.run()
	tcp_results = exp.results
    except Exception as e:
    	log("e", "Error running TCP connect test: " + str(e))

    try:
	exp = ConfigurableTracerouteExperiment(input_file)
    	exp.run()
	traceroute_results = exp.results
    except Exception as e:
    	log("e", "Error running traceroute test: " + str(e))

    return http_results, dns_results, ping_results, tcp_results, traceroute_results

def prep_results(operator, experiment_name):
    results = {}
    run_id = str(int(conf["run_id"]) + 1)
    ip = getmyip()
    esttime = getESTTime()
    localtime = datetime.now().isoformat()
    country = geolocate(ip)[0]
    city = geolocate(ip)[1]

    meta = { "est_time"		: esttime,
	     "local_time"	: localtime,
	     "client_tag"   	: conf["client_tag"],
	     "exp_name"		: experiment_name,
	     "country"		: country,
	     "city"		: city,
	     "operator" 	: operator,
	     "ext_ip"		: ip,
	     "run_id"		: run_id
	   }

    conf.set("run_id", run_id)
    conf.update()
    results["meta"] = meta

    return results, run_id
