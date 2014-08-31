import os
import logging
import getpass

# centinel user
current_user    = getpass.getuser()
centinel_home   = os.path.join(os.path.expanduser('~'+current_user), '.centinel')

# directory structure
experiments_dir = os.path.join(os.path.dirname(__file__), "experiments")
data_dir        = os.path.join(os.path.dirname(__file__), "data")
results_dir     = os.path.join(centinel_home, 'results')

# logging
log_level       = logging.INFO 
log_file        = None # os.path.join(centinel_home, "centinel.log")
log_format      = '%(levelname)s: %(message)s'

# server
server_url      = "http://127.0.0.1:5000"

# proxy
proxy_type      = None # "socks" or "http"
proxy_url       = None # "http://127.0.0.1:9050"
proxy           = {proxy_type : proxy_url} if proxy_type else None
