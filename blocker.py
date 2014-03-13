import experiments.tcp_connect

EXPERIMENTS = []

if __name__ == "__main__":
    with open("data/tcp_connect.txt") as fh:
        exp = experiments.tcp_connect.TCPConnectExperiment(fh)        
        print exp.run()
