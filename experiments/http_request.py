import httplib

class HTTPRequestExperiment:
    name = "http_request"

    def __init__(self, input_file=None, result_file=None):
        if not input_file:
            raise Exception

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
            self.result_file.write(self.result)

    def http_request(self):
        try:
            conn = httplib.HTTPConnection(self.host)
            conn.request("GET", self.path)
            response = conn.getresponse()
            conn.close()

            msg = "%s %s" % (response.status, response.reason)
        except Exception as err:
            msg = err.strerror

        self.result = "%s %s %s" % (self.host, self.path, msg)
