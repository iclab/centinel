import experiments.tcp_connect
import experiments.http_request

EXPERIMENTS = []

if __name__ == "__main__":
    with open("data/tcp_connect.txt") as fh:
        exp = experiments.tcp_connect.TCPConnectExperiment(fh)        
        print exp.run()

    with open("data/http_request.txt") as fh:
        exp = experiments.http_request.HTTPRequestExperiment(fh)        
        print exp.run()
