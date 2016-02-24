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

    # if the experiment produces files that are not
    # to be included in the json file, it should
    # keep them in this dictionary.
    # { "file1_name.extention" : "[file1_contents]",
    #   "file2_name.extention" : "[file2_contents]",
    #   ... }
    # these files will be compressed when being stored
    external_results = None

    # an experiment can have external parameters
    # that are usually set by the scheduler.
    params = {}

    def run(self):
        raise NotImplementedError
