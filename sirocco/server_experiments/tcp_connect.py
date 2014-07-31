import socket

from centinel.experiment import Experiment

class TCPConnectExperiment(Experiment):
    name = "tcp_connect"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.host = None
        self.port = None

    def run(self):
        for line in self.input_file:
            self.host, self.port = line.strip().split(' ')
            self.tcp_connect()

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
