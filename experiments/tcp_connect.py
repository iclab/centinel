import socket
import json

class TCPConnectExperiment:
    name = "tcp_connect"

    def __init__(self, input_file, result_file):
        self.input_file = input_file
        self.result_file = result_file
        self.results = []
        self.host = None
        self.port = None

    def process_input(self):
        for line in self.input_file:
            yield line.strip().split(' ')

    def run(self):
        for (self.host, self.port) in self.process_input():
            self.tcp_connect()

        json.dump(self.results, self.result_file)

    def tcp_connect(self):
        result = {
            "host" : self.host,
            "port" : self.port
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, int(self.port)))
            sock.close()
            result["success"] = "true"
        except Exception as err:
            result["failure"] = str(err)

        self.results.append(result)
