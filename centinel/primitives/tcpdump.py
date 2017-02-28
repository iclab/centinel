# Ben Jones bjones99@gatech.edu
# Georgia Tech Fall 2014
#
# tcpdump.py: interface to tcpdump to stop and start captures and do
# second passes over existing pcaps

from base64 import b64encode
import logging
import os
import tempfile


# local imports
import centinel
from centinel import command


class Tcpdump():
    """Class to interface between tcpdump and Python"""

    def __init__(self, filename=None, pcap_args=None):
        if filename is None:
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.close()
            filename = temp_file.name
        self.filename = filename
        # don't change this to default value because it is a mutable
        # type and whatever you change it to will become the new
        # default value until the interpreter is restarted
        if pcap_args is None:
            # use the centinel configured tcpdump options if available
            # (if not specified by the user, this will be -i any, so
            # the same as below
            if 'tcpdump_params' in centinel.conf['experiments']:
                pcap_args = centinel.conf['experiments']['tcpdump_params']
            # for backwards compatability, ensure that we give some
            # pcap args for what to capture
            else:
                pcap_args = ["-i", "any"]
                logging.warning("Global config not available, so falling "
                                "back on -i any pcap args")
        self.pcap_args = pcap_args

    def start(self):
        cmd = ['sudo', 'tcpdump', '-w', self.filename]
        cmd.extend(self.pcap_args)
        self.caller = command.Command(cmd, _tcpdump_callback)
        self.caller.start()

    def stop(self):
        if self.caller is not None:
            self.caller.stop()

    def post_processing(self, out_filter, out_file=None):
        if out_file is None:
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.close()
            out_file = temp_file.name
        cmd = ['tcpdump', '-r', self.filename, '-w', out_file]
        caller = command.Command(cmd, _tcpdump_callback)
        caller.start()

    def b64_output(self):
        with open(self.filename, 'r') as file_p:
            return b64encode(file_p.read())

    def pcap(self):
        with open(self.filename, 'r') as file_p:
            return file_p.read()

    def pcap_filename(self):
        return self.filename

    def delete(self):
        os.remove(self.filename)


def _tcpdump_callback(self, line, kill_switch):
    """Callback function to handle tcpdump"""

    line = line.lower()
    if ("listening" in line) or ("reading" in line):
        self.started = True
    if ("no suitable device" in line):
        self.error = True
        self.kill_switch()
    if "by kernel" in line:
        self.stopped = True
