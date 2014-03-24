import os

from datetime import datetime
from experiments import *

RESULTS_DIR = "results"
DATA_DIR    = "data"

EXPERIMENTS = [
    tcp_connect.TCPConnectExperiment,
    http_request.HTTPRequestExperiment
]

def get_result_file(experiment_name):
    result_file = "%s-%s.txt" % (datetime.now().isoformat(), experiment_name)
    return os.path.join(RESULTS_DIR, result_file)

def get_input_file(experiment_name):
    input_file = "%s.txt" % (experiment_name)
    return os.path.join(DATA_DIR, input_file)

def run():
    for exp in EXPERIMENTS:
        input_file = get_input_file(exp.name)

        if not os.path.isfile(input_file):
            print "Input file for %s does not exist!" % exp.name
            continue

        input_file = open(input_file)

        result_file = get_result_file(exp.name)
        result_file = open(result_file, "w")

        exp = exp(input_file, result_file)
        exp.run()

        result_file.close()
        input_file.close()

if __name__ == "__main__":
    run()
