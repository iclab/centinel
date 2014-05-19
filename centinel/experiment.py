class ExperimentList(type):
    experiments = {}
    def __init__(cls, name, bases, attrs):
        if name != "Experiment":
            ExperimentList.experiments[cls.name] = cls

class Experiment:
    __metaclass__ = ExperimentList
    def __init__(self, input_file):
        self.results = []
        self.input_file = input_file

    def run(self):
        raise NotImplementedError
