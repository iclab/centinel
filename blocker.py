import os

from datetime import datetime

import experiments.tcp_connect
import experiments.http_request

RESULTS_DIR = "results"

def run():
    experiments = [
        experiments.tcp_connect,
        experiments.http_request
    ]

    for exp in experiments:
        result_file = "%s%s.txt" % (datetime.now().isoformat(), exp.name)
        result_file = os.path.join(RESULTS_DIR, result_file)
        result_file = open(result_file, "w")

        with open("data/tcp_connect.txt") as in_fh:
            exp = experiments.tcp_connect.TCPConnectExperiment(in_fh, result_file)
            print exp.run()

    with open("data/http_request.txt") as fh:
        exp = experiments.http_request.HTTPRequestExperiment(fh)
        print exp.run()

if __name__ == "__main__":
    run()
