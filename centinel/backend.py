import requests
import config

def request(slug):
    url = "%s%s" % (config.server_url, slug)
    req = requests.get(url)

    if req.status_code != requests.codes.ok:
        raise req.raise_for_status()

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
        requests.post(url, files=file)

    if req.status_code != requests.codes.ok:
        raise req.raise_for_status()
