#!/usr/bin/python
# openvpn.py: library to handle starting and stopping openvpn instances

import subprocess
import threading
import time
import os
import signal
import logging


class OpenVPN:
    def __init__(self, config_file=None, auth_file=None, crt_file=None,
                 tls_auth=None, key_direction=None, timeout=60):
        self.started = False
        self.stopped = False
        self.error = False
        self.notifications = ""
        self.auth_file = auth_file
        self.crt_file = crt_file
        self.tls_auth = tls_auth
        self.key_dir = key_direction
        self.config_file = config_file
        self.thread = threading.Thread(target=self._invoke_openvpn)
        self.thread.setDaemon(1)
        self.timeout = timeout

        # sanity check: tls_auth and key_direction must present together
        if (tls_auth is not None and key_direction is None) or \
                (tls_auth is None and key_direction is not None):
            logging.error("tls_auth and key_direction must present "
                          "together! Or none of them would be included "
                          "in command options")

    def _invoke_openvpn(self):
        cmd = ['sudo', 'openvpn', '--script-security', '2']
        # --config must be the first parameter, since otherwise
        # other specified options might not be able to overwrite
        # the wrong, relative-path options in config file
        if self.config_file is not None:
            cmd.extend(['--config', self.config_file])
        if self.crt_file is not None:
            cmd.extend(['--ca', self.crt_file])
        if self.tls_auth is not None and self.key_dir is not None:
            cmd.extend(['--tls-auth', self.tls_auth, self.key_dir])
        if self.auth_file is not None:
            cmd.extend(['--auth-user-pass', self.auth_file])

        self.process = subprocess.Popen(cmd,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        preexec_fn=os.setsid)
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
        if "ERROR:" in line or "Cannot resolve host address:" in line:
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
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        self.thread.join(timeout)
        if self.stopped:
            print "stopped"
        else:
            print "not stopped"
            print self.notifications
