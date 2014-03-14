import httplib

class HTTPRequestExperiment:
    def __init__(self, input=None):
        if not input:
            raise Exception

        self.input = input
        self.host = None
        self.path = None

    def process_input(self):
        for line in self.input:
            yield line.split('/', 1)

    def run(self):
        for (self.host, self.path) in self.process_input():
            err = self.http_request()

            if err: return err

    def http_request(self):
        try:
            conn = httplib.HTTPConnection(self.host)
            conn.request("GET", self.path)
            response = conn.getresponse()
            conn.close()

            print response.status, response.reason
        except:
            # return exception
            return 
