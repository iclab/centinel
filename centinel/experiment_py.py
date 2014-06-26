class ExperimentList(type):
    experiments = {}
    def __init__(cls, name, bases, attrs):
        if name != "Experiment":
            ExperimentList.experiments[cls.name] = cls

class Experiment:
    __metaclass__ = ExperimentList

    def run(self):
        raise NotImplementedError
