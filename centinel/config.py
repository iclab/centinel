import os
import getpass

# centinel user 
current_user    = getpass.getuser()

# directory structure
centinel_home   = os.path.join(os.path.expanduser('~'+current_user), '.centinel')
experiments_dir = os.path.join(os.path.dirname(__file__), "experiments")
data_dir        = os.path.join(os.path.dirname(__file__), "data")
results_dir     = os.path.join(centinel_home, 'results')
