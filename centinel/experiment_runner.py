import os
import sys
import json
import glob
import imp
import getpass
from configurable.http import ConfigurableHTTPRequestExperiment
from configurable.tcp_connect import ConfigurableTCPConnectExperiment
from configurable.ping	import ConfigurablePingExperiment
from configurable.dns_exp	import ConfigurableDNSExperiment

from datetime import datetime

from experiment_py import Experiment, ExperimentList
from client_config import client_conf

conf = client_conf()

EXPERIMENTS_DIR = conf.c['experiments_py_dir']
DATA_DIR        = conf.c['experiment_data_dir']
RESULTS_DIR	= conf.c['results_dir']
CONF_EXP_DIR	= conf.c['configurable_experiments_dir']

def get_results_dir():
    return RESULTS_DIR

def get_result_file(results_dir):
    result_file = "result-%s.json" % (datetime.now().isoformat())
    return os.path.join(results_dir, result_file)

def get_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return os.path.join(DATA_DIR, input_file)

def get_conf_input_file(experiment_name):
    input_file = "%s.cfg" % (experiment_name)
    return os.path.join(CONF_EXP_DIR, input_file)

def load_experiments():
    # look for experiments in experiments directory
    for path in glob.glob(os.path.join(EXPERIMENTS_DIR,'[!_]*.py')):
        # get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        # load the experiment
        imp.load_source(name, path)

    # return dict of experiment names and classes
    return ExperimentList.experiments

def load_conf_experiments():
    exp_list = []
    # look for experiments in experiments directory
    for path in glob.glob(os.path.join(CONF_EXP_DIR,'[!_]*.cfg')):
        # get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        exp_list.append(name)

    # return dict of experiment names and classes
    return exp_list
    

def run(selection = []):
    results_dir = get_results_dir()    

    if not selection:
	print "No experiments specified, running all..."
	run_all = True
    else:
	run_all = False
    print results_dir
    if not os.path.exists(results_dir):
        print "Creating results directory in %s" % (results_dir)
        os.makedirs(results_dir)

    result_file = get_result_file(results_dir)
    result_file = open(result_file, "w")
    results = {}

    experiments = load_experiments()
    conf_experiments = load_conf_experiments()

    if run_all:
        for name, Exp in experiments.items():
	    results[name] = execute_experiment(name, Exp)
	for name in conf_experiments:
	    results[name] = execute_conf_experiment(name)
    else:
	ran = []
        for name in selection:
	    if not name in experiments.keys():
		#print "Experiment %s not found." % (name)
		continue
	    Exp = experiments[name]
	    results[name] = execute_experiment(name, Exp)
	    ran.append(name);
	
	for name in selection:
	    if not name in conf_experiments:
		continue
	    http_results, dns_results, ping_results, tcp_results = execute_conf_experiment(name)
	    if http_results:
		results[name + ".http"] = http_results
	    if dns_results:
		results[name + ".dns"] = dns_results
	    if tcp_results:
		results[name + ".tcp"] = tcp_results
	    if ping_results:
		results[name + ".ping"] = ping_results
	    ran.append(name)

    for name in selection:
	if name not in ran:
	    print "Experiment %s not found." %(name)


    json.dump(results, result_file)
    result_file.close()

    print "All experiments over. Check results."

def execute_experiment(name, Exp):
    results = {}
    input_file = get_input_file(name)

    if not os.path.isfile(input_file):
	print "No input file found for %s. Skipping test." % (name)
	return
    
    print "Reading input from %s" % (input_file)
    input_file = open(input_file)

    try:
    	print "Running %s test." % (name)
    	exp = Exp(input_file)
    	exp.run()
    except Exception, e:
    	print "Error: %s", str(e)

    input_file.close()
    return exp.results

def execute_conf_experiment(name):
    results = {}
    input_file = get_conf_input_file(name)

    if not os.path.isfile(input_file):
	print "No input file found for %s. Skipping test." % (name)
	return
    
    print "Reading config experiment from %s" % (input_file)

    try:
    	print "Running %s test." % (name)
    	exp = ConfigurableHTTPRequestExperiment(input_file)
    	exp.run()
	http_results = exp.results
	exp = ConfigurableDNSExperiment(input_file)
    	exp.run()
	dns_results = exp.results
	exp = ConfigurablePingExperiment(input_file)
    	exp.run()
	ping_results = exp.results
	exp = ConfigurableTCPConnectExperiment(input_file)
    	exp.run()
	tcp_results = exp.results
    except Exception, e:
    	print "Error: %s", str(e)

    return http_results, dns_results, ping_results, tcp_results
