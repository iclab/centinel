#!/usr/bin/env python

import sys
import logging

from sirocco.server import Server
from utils.logger import *

if len(sys.argv) > 1 and sys.argv[1] == "--local":
    local_server = True
else:
    local_server = False

try:
    print open("sirocco_server_ascii_art", "r").read()
    logging.basicConfig(filename="server.log", level=logging.DEBUG)
    server = Server(local=local_server)
    server.run()
except Exception as e:
    log("e", "Error running server: " + str(e))
