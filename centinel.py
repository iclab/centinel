#! /usr/bin/python

import os

centinel_dir=os.path.abspath(os.path.dirname(__file__))
os.chdir(centinel_dir)

import sys
import os
from subprocess import call
from client_run import centinel_run
import os.path
import shutil


if centinel_run(sys.argv) == 2:
    print "Client update downloaded."
    if os.path.isfile("update.tar.bz2"):
	print "Removing old Centinel directories..."
	shutil.move('update.tar.bz2', '/tmp/centinel_update.tar.bz2')
	shutil.rmtree(centinel_dir, ignore_errors=True)
	os.chdir("/tmp")
	print "Done."
	print "Unpacking new Centinel package..."
	shutil.rmtree("/tmp/centinel_update", ignore_errors=True)
	os.mkdir("/tmp/centinel_update")
	call(("tar -jxf /tmp/centinel_update.tar.bz2 -C " + "/tmp/centinel_update/" ).split())
	shutil.copytree("/tmp/centinel_update/centinel_latest", centinel_dir)
	os.remove("/tmp/centinel_update.tar.bz2")
	print "Done."
	os.chdir(centinel_dir)
	print os.path.join(centinel_dir, "prepare.sh")
	call((os.path.join(centinel_dir, "prepare.sh")).split())
	print os.path.join(centinel_dir, "init_client.py") + " --offline"
	call((os.path.join(centinel_dir, "init_client.py") + " --offline").split())
    else:
        print "Update package not found!"

    print "Restarting Centinel client..."
    print os.path.join(centinel_dir, "centinel.py")
    os.execl(os.path.join(centinel_dir, "centinel.py"), " ".join(sys.argv))
