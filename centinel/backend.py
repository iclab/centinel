import requests
import config

def get_recommended_versions():
    return request("/versions")

def get_experiments():
    return request("/experiments")

def get_results():
    return request("/results")

def get_clients():
    return request("/clients")

def request(slug):
    url = "%s%s" % (config.server_url, slug)
    req = requests.get(url)
    return req.json()
