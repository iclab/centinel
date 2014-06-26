class ExperimentList(type):
    experiments = {}
    def __init__(cls, name, bases, attrs):
        if name != "Experiment" and name not in [ "ConfigurableDNSExperiment", "ConfigurableHTTPRequestExperiment", "ConfigurableTCPConnectExperiment", "ConfigurablePingExperiment"]:
            ExperimentList.experiments[cls.name] = cls

class Experiment:
    __metaclass__ = ExperimentList

    def run(self):
        raise NotImplementedError
