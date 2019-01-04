#!/usr/bin/python
# openvpn.py: library to handle starting and stopping openvpn instances

import logging
import os
import signal
import subprocess
import threading
import time

class VPNConnectionError(Exception):
    def __init__(self, value, log):
        self.value = value
        self.log = log

    def __str__(self):
        return repr(self.value)

class OpenVPN:
    connected_instances = []

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
        """
        Start OpenVPN and block until the connection is opened or there is
        an error
        :param timeout: time in seconds to wait for process to start
        :return:
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
            logging.info("OpenVPN connected")
            # append instance to connected list
            OpenVPN.connected_instances.append(self)
        else:
            logging.warn('OpenVPN not started')
            log_lines = self.notifications.split('\n')
            for line in log_lines:
                logging.warn("OpenVPN output:\t\t%s" % line)
            raise VPNConnectionError("OpenVPN not started", log_lines)

    def stop(self, timeout=None):
        """
        Stop OpenVPN process group
        :param timeout: time in seconds to wait for process to stop
        :return:
        """
        if not timeout:
            timeout = self.timeout

        process_group_id = os.getpgid(self.process.pid)
        try:
            os.killpg(process_group_id, signal.SIGTERM)
        except OSError:
            # Because sometimes we have to sudo to send the signal
            cmd = ['sudo', 'kill', '-' + str(process_group_id)]
            process = subprocess.call(cmd)

        self.thread.join(timeout)
        if self.stopped:
            logging.info("OpenVPN stopped")
            if self in OpenVPN.connected_instances:
                OpenVPN.connected_instances.remove(self)
        else:
            logging.error("Cannot stop OpenVPN!")
            for line in self.notifications.split('\n'):
                logging.warn("OpenVPN output:\t\t%s" % line)
