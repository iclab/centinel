import socket

class TCPConnectExperiment:
    name = "tcp_connect"

    def __init__(self, input_file=None, result_file=None):
        if not input_file:
            raise Exception

        self.input_file = input_file
        self.result_file = result_file
        self.result = None
        self.host = None
        self.port = None

    def process_input(self):
        for line in self.input_file:
            yield line.strip().split(' ')

    def run(self):
        for (self.host, self.port) in self.process_input():
            self.tcp_connect()
            self.result_file.write(self.result)

    def tcp_connect(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, int(self.port)))
            s.close()
            msg = True
        except Exception as err:
            msg = err.strerror

        self.result = "%s:%s %s" % (self.host, self.port, msg)
