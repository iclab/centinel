from datetime import datetime
import experiments.tcp_connect
import experiments.http_request

def run():
    with open("results/"+datetime.now().isoformat()+"-tcp_connect.txt", "w") as out_fh:
        with open("data/tcp_connect.txt") as in_fh:
            exp = experiments.tcp_connect.TCPConnectExperiment(in_fh, out_fh)
            print exp.run()

    with open("data/http_request.txt") as fh:
        exp = experiments.http_request.HTTPRequestExperiment(fh)
        print exp.run()

if __name__ == "__main__":
    run()
