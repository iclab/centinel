#!/usr/bin/env python

import sys

from centinel import client
selection = sys.argv
selection.pop(0)
client.run(selection)
