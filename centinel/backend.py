import os
import glob
import requests

import config

def request(slug):
    url = "%s%s" % (config.server_url, slug)
    req = requests.get(url)

    req.raise_for_status()
    return req.json()

def get_recommended_versions():
    return request("/versions")

def get_experiments():
    return request("/experiments")

def get_results():
    return request("/results")

def get_clients():
    return request("/clients")

def submit_result(file_name):
    with open(file_name) as result_file:
        file = {'result' : result_file}
        url = "%s%s" % (config.server_url, "/results")
        req = requests.post(url, files=file)

    req.raise_for_status()

def sync():
    # send all results
    for path in glob.glob(os.path.join(config.results_dir,'[!_]*.json')):
        try:
            submit_result(path)
        except Exception, e:
            logging.error("Unable to send result file %s" % (path))
