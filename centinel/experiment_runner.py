import os
import sys
import json
import glob
import imp
import getpass

from datetime import datetime

from experiment import Experiment, ExperimentList
from client_config import client_conf

conf = client_conf()

EXPERIMENTS_DIR = conf.c['experiments_dir']
DATA_DIR        = conf.c['data_dir']
RESULTS_DIR	= conf.c['results_dir']

def get_results_dir():
    return RESULTS_DIR

def get_result_file(results_dir):
    result_file = "result-%s.json" % (datetime.now().isoformat())
    return os.path.join(results_dir, result_file)

def get_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return os.path.join(DATA_DIR, input_file)

def load_experiments():
    # look for experiments in experiments directory
    for path in glob.glob(os.path.join(EXPERIMENTS_DIR,'[!_]*.py')):
        # get name of file and path
        name, ext = os.path.splitext(os.path.basename(path))
        # load the experiment
        imp.load_source(name, path)

    # return dict of experiment names and classes
    return ExperimentList.experiments

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

    if run_all:
        for name, Exp in experiments.items():
	    results[name] = execute_experiment(name, Exp)
    else:
        for name in selection:
	    if not name in experiments.keys():
		print "Experiment %s not found." % (name)
		continue
	    Exp = experiments[name]
	    results[name] = execute_experiment(name, Exp)
	    

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

