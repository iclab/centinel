import socket

class TCPConnectExperiment():
    def __init__(self, input=None):
        if not input:
            raise Exception

        self.input = input
        self.host = None
        self.port = None

    def process_input(self):
        for line in self.input:
            yield line.split(' ')

    def run(self):
        for (self.host, self.port) in self.process_input():
            err = self.tcp_connect()

            if err: return err

    def tcp_connect(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, int(self.port)))
            s.close()
        except socket.error as msg:
            return msg
