import logging
import requests

from centinel.experiment import Experiment


class SSLStripExperiment(Experiment):
    name = "ssl_strip"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []

    def run(self):
        for line in self.input_file:
            site = line.strip()
            self.ssl_strip_test(site)

    def ssl_strip_test(self, site):
        result = {
            "site": site,
        }

        logging.info("Checking %s for SSL stripping" % (site))
        req = requests.get(site, allow_redirects=False)
        result["headers"] = dict(req.headers)
        result["status"] = req.status_code
        # if the status code is not 3xx or the redirect location does
        # not contain https, then this is a bad site
        result["success"] = True
        if (req.status_code > 399) or (req.status_code < 300):
            result["success"] = False
        elif (("location" in req.headers) and
              ("https" not in req.headers["location"])):
            result["success"] = False
        self.results.append(result)
