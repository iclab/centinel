import sys
import json
import glob
import imp

from os.path import join, basename, splitext, dirname, exists, isfile
from datetime import datetime

from experiment import Experiment, ExperimentList

EXPERIMENTS_DIR = join(dirname(__file__), "experiments")
RESULTS_DIR     = join(dirname(__file__), "results")
DATA_DIR        = join(dirname(__file__), "data")

def get_result_file():
    result_file = "result-%s.json" % (datetime.now().isoformat())
    return join(RESULTS_DIR, result_file)

def get_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return join(DATA_DIR, input_file)

def load_experiments(dir):
    for path in glob.glob(join(dir,'[!_]*.py')):
        name, ext = splitext(basename(path))
        _ = imp.load_source(name, path)

    return ExperimentList.experiments

def run():
    experiments = load_experiments(EXPERIMENTS_DIR)

    if not exists(RESULTS_DIR):
        print "Creating results directory in %s" % (RESULTS_DIR)
        os.makedirs(RESULTS_DIR)

    result_file = get_result_file()
    result_file = open(result_file, "w")
    results = {}

    for name, exp in experiments.items():
        input_file = get_input_file(name)

        if not isfile(input_file):
            print "Input file for %s does not exist!" % name
            continue

        print "Reading input from %s" % (input_file)
        input_file = open(input_file)

        exp = exp(input_file)
        print "Running %s test." % (name)
        exp.run()

        input_file.close()

        results[name] = exp.results

    json.dump(results, result_file)
    result_file.close()

    print "All experiments over. Check results."
