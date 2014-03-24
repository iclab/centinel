import json
import httplib

class HTTPRequestExperiment:
    name = "http_request"

    def __init__(self, input_file, result_file):
        self.input_file  = input_file
        self.result_file = result_file
        self.results = []
        self.host = None
        self.path = "/"

    def run(self):
        for line in self.input_file:
            self.host = line.strip()
            self.http_request()

        json.dump(self.results, self.result_file)

    def http_request(self):
        request  = {
            "host"  : self.host,
            "path"  : self.path,
            "method": "GET"
        }

        response = {}
        
        try:
            conn = httplib.HTTPConnection(self.host)
            conn.request("GET", self.path)

            resp = conn.getresponse()
            response["status"] = resp.status
            response["reason"] = resp.reason

            headers = dict(resp.getheaders())
            response["headers"] = headers

            body = resp.read()
            response["body"] = body

            conn.close()
        except Exception as err:
            response["failure"] = str(err)

        result = {
            "response" : response,
            "request"  : request
        }
        
        self.results.append(result)
