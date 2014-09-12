#!/usr/bin/python
# openvpn.py: library to handle starting and stopping openvpn instances

import subprocess
import threading
import time


class OpenVPN():
    def __init__(self, config_file=None, auth_file=None, timeout=10):
        self.started = False
        self.stopped = False
        self.error = False
        self.notifications = ""
        self.auth_file = auth_file
        self.config_file = config_file
        self.thread = threading.Thread(target=self._invoke_openvpn)
        self.thread.setDaemon(1)
        self.timeout = timeout

    def _invoke_openvpn(self):
        if self.auth_file is None:
            cmd = ['sudo', 'openvpn', '--script-security', '2',
                   '--config', self.config_file]
        else:
            cmd = ['sudo', 'openvpn', '--script-security', '2',
                   '--config', self.config_file,
                   '--auth-user-pass', self.auth_file]
        self.process = subprocess.Popen(cmd,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        self.kill_switch = self.process.terminate
        self.starting = True
        while True:
            line = self.process.stdout.readline().strip()
            if not line:
                break
            self.output_callback(line, self.process.terminate)

    def output_callback(self, line, kill_switch):
        """Set status of openvpn according to what we process"""

        self.notifications += line + "\n"

        if "Initialization Sequence Completed" in line:
            self.started = True
        if "ERROR:" in line:
            self.error = True
        if "process exiting" in line:
            self.stopped = True

    def start(self, timeout=None):
        """Start openvpn and block until the connection is opened or there is
        an error

        """
        if not timeout:
            timeout = self.timeout
        self.thread.start()
        start_time = time.time()
        while start_time + timeout > time.time():
            self.thread.join(1)
            if self.error or self.started:
                break
        if self.started:
            print "openvpn started"
        else:
            print "openvpn not started"
            print self.notifications

    def stop(self, timeout=None):
        """Stop openvpn"""
        if not timeout:
            timeout = self.timeout
        self.kill_switch()
        self.thread.join(timeout)
        if self.stopped:
            print "stopped"
        else:
            print "not stopped"
            print self.notifications
