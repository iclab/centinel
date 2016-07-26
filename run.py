#!/usr/bin/python

import centinel.cli
import os
import os.path
import sys

PID_FILE = "/tmp/centinel.lock"

if __name__ == "__main__":
    if os.path.isfile(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read()
            print "Centinel already running (PID = %s)" % pid
            print "Lock file address: %s" % PID_FILE
        sys.exit(1)

    try:
        f = open(PID_FILE, "w")
        f.write("%d" % os.getpid())
        f.close()
    except Exception as exp:
        sys.stderr.write('Error to writing the'
                         ' lock file: %s\n' % exp)
        sys.exit(1)

    try:
        centinel.cli.run()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print "Keyboard interrupt received, exiting..."
    except Exception as exp:
        sys.stderr.write("%s" % exp)

    try:
        os.remove(PID_FILE)
    except Exception as exp:
        sys.stderr.write("Failed to remove lock file %s: %s" % (PID_FILE, exp))
