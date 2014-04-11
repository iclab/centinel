import os
import sys
import json

import utils

from datetime import datetime
from experiments import *

RESULTS_DIR = "results"
DATA_DIR    = "data"

EXPERIMENTS = {
    "turkey"       : turkey.TurkeyExperiment
}

def get_result_file():
    result_file = "result-%s.txt" % (datetime.now().isoformat())
    return os.path.join(RESULTS_DIR, result_file)

def get_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return os.path.join(DATA_DIR, input_file)

def run():        
    result_file = get_result_file()
    result_file = open(result_file, "w")
    results = {}

    for name, exp in EXPERIMENTS.items():
        input_file = get_input_file(name)

        if not os.path.isfile(input_file):
            print "Input file for %s does not exist!" % name
            return

        input_file = open(input_file)

        exp = exp(input_file)
        exp.run()

        input_file.close()

        results[name] = exp.results

    json.dump(results, result_file)
    result_file.close()

if __name__ == "__main__":
    run()
