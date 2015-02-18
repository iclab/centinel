class ExperimentList(type):
    experiments = {}
    def __init__(cls, name, bases, attrs):
        if name != "Experiment":
            ExperimentList.experiments[cls.name] = cls

class Experiment:
    __metaclass__ = ExperimentList

    # a list of input files that can be
    # used in order to make use of more than
    # one input file. If none specified, the
    # [experiment name].txt will be used instead.
    input_files = None

    # this should be set to True if the experiment
    # does its own tcpdump recording.
    overrides_tcpdump = False

    def run(self):
        raise NotImplementedError
