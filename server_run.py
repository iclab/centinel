#!/usr/bin/env python

import sys

from centinel.server import Server

try:
    server = Server()
    server.run()
except Exception as e:
    print "Error running server: " + str(e)