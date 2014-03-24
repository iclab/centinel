import json
import httplib

class HTTPRequestExperiment:
    name = "http_request"

    def __init__(self, input_file=None, result_file=None):
        self.input_file = input_file
        self.result_file = result_file
        self.host = None
        self.path = "/"

    def process_input(self):
        for line in self.input_file:
            yield line.strip()

    def run(self):
        for self.host in self.process_input():
            self.http_request()
            json.dump(self.result, self.result_file)

    def http_request(self):
        self.result = {}
        
        try:
            conn = httplib.HTTPConnection(self.host)
            conn.request("GET", self.path)

            response = conn.getresponse()
            body     = response.read()
            headers  = response.getheaders()

            conn.close()

            self.result = {
                "http_version" : response.version,
                "body"         : body,
                "headers"      : dict(headers),
                "status"       : response.status,
                "reason"       : response.reason,
            }

        except Exception as err:
            self.result = {
                "failure" : str(err)
            }

        self.result["host"] = self.host
        self.result["path"] = self.path
