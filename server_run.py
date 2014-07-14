#!/usr/bin/env python

import sys
import logging

from centinel.server import Server
from centinel.utils.logger import *

try:
    print open("sirocco_server_ascii_art", "r").read()
    logging.basicConfig(filename="server.log", level=logging.DEBUG)
    server = Server()
    server.run()
except Exception as e:
    log("e", "Error running server: " + str(e))
