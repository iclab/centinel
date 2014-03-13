import socket

def tcp_connect(host, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
    except socket.error as msg:
        return msg

class TCPConnectExperiment():
    def process_input(self, input):
        for line in input:
            yield line.split(' ')
        
    def run(self, input):
        if not input:
            raise Exception

        for (host, port) in self.process_input(input):
            err = tcp_connect(host, int(port))

            if err: return err
