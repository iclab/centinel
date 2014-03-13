import experiments.tcp_connect

EXPERIMENTS = []

if __name__ == "__main__":
    exp = experiments.tcp_connect.TCPConnectExperiment()

    with open("data/tcp_connect.txt") as fh:
        print exp.run(fh)
