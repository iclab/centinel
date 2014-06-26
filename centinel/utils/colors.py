import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def update_progress(progress):
    sys.stdout.write( '\r[{0}] {1}%'.format('#'*(progress/5), progress) )