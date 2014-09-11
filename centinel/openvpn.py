#!/usr/bin/python
# Ben Jones bjones99@gatech.edu
# Summer 2014
# openvpn.py: library to handle starting and stopping openvpn instances

import subprocess
import threading
import time


class OpenVPN():
    def __init__(self, ):
        self.started = False
        self.stopped = False
        self.error = False
        self.notifications = ""

    def _invoke_openvpn(self):
        if self.authFile is None:
            cmd = ['sudo', 'openvpn', '--script-security', '2',
                   '--config', self.configFile]
        else:
            cmd = ['sudo', 'openvpn', '--script-security', '2',
                   '--config', self.configFile,
                   '--auth-user-pass', self.authFile]
        self.process = subprocess.Popen(cmd,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        self.killswitch = self.process.terminate
        self.starting = True
        while True:
            line = self.process.stdout.readline().strip()
            if not line:
                break
            self.output_callback(line, self.process.terminate)

    def output_callback(self, line, killswitch):
        """Set status of openvpn according to what we process"""

        self.notifications += line + "\n"

        if "Initialization Sequence Completed" in line:
            self.started = True
        if "ERROR:" in line:
            self.error = True
        if "process exiting" in line:
            self.stopped = True
        return

    def start(self, configFile, timeout=10, authFile=None):
        """Start openvpn and block until the connection is opened or there is
        an error

        """
        self.authFile = authFile
        self.configFile = configFile
        self.thread = threading.Thread(target=self._invoke_openvpn)
        self.thread.setDaemon(1)
        self.thread.start()
        startTime = time.time()
        while startTime + timeout > time.time():
            self.thread.join(1)
            if self.error or self.started:
                break
        if self.started:
            print "openvpn started"
        else:
            print "openvpn not started"
            print self.notifications
        return

    def stop(self, timeout=10):
        """Stop openvpn"""
        self.killswitch()
        self.thread.join(timeout)
        if self.stopped:
            print "stopped"
        else:
            print "not stopped"
            print self.notifications
        return
