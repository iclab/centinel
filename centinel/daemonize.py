#!/usr/bin/python
#
# daemonize.py: functionality to make centinel run in the background

import os
import shutil
import stat
import tempfile


def create_script_for_location(content, destination):
    """Create a script with the given content, mv it to the
    destination, and make it executable

    Parameters:
    content- the content to put in the script
    destination- the directory to copy to

    Note: due to constraints on os.rename, destination must be an
    absolute path to a file, not just a directory

    """
    temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
    temp.write(content)
    temp.close()
    shutil.move(temp.name, destination)
    cur_perms = os.stat(destination).st_mode
    set_perms = cur_perms | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR
    os.chmod(destination, set_perms)


def daemonize(package, bin_loc, user):
    """Create crontab entries to run centinel every hour and
    autoupdate every day

    Parameters:

    package- name of the currently installed package (will be used for
        autoupdate). If this parameter is None, the autoupdater will
        not be used

    bin_loc- location of the centinel binary/script.

    Note: this works by creating temporary files, adding the content
    of the cron scripts to these temporary files, moving these files
    into the appropriate cron folders, and making these scripts
    executable

    Note: if the script already exists, this will delete it

    """

    path = "/etc/cron.hourly/centinel-" + user

    if user != "root":
        # create a script to run centinel every hour as the current user
        hourly = "".join(["#!/bin/bash\n",
                          "# cron job for centinel\n",
                          "su ", user, " -c '", bin_loc, " --sync'\n",
                          "su ", user, " -c '", bin_loc, "'\n",
                          "su ", user, " -c '", bin_loc, " --sync'\n"])
    else:
        # create a script to run centinel every hour as root
        hourly = "".join(["#!/bin/bash\n",
                          "# cron job for centinel\n",
                          bin_loc, " --sync\n",
                          bin_loc, "\n",
                          bin_loc, " --sync\n"])

    create_script_for_location(hourly, path)

    # create a script to get the client to autoupdate every day
    if package is None:
        return
    updater = "".join(["#!/bin/bash\n",
                      "# autoupdater for centinel\n"
                      "sudo pip install --upgrade ", package, "\n"])
    create_script_for_location(updater, "/etc/cron.daily/centinel-autoupdate")
    print "Successfully created cron jobs for user " + user

