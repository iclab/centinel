#
# Abbas Razaghpanah (arazaghpanah@cs.stonybrook.edu)
# February 2015, Stony Brook University
#
# tracerout.py: interface to system traceroute
# for this to work, traceroute has to be installed
# and accessible.


import time


from centinel import command


def traceroute(url, method="icmp", cmd_arguments=[]):
    """This function uses centinel.command to issue
    a traceroute command, wait for it to finish execution and
    parse the results out to a dictionary.

    Params:
    url- the URL to be queried

    method- the packet type used for traceroute, ICMP by default

    cmd_arguments- the list of arguments that need to be passed
    to traceroute.

    """

    # the method specified by the function parameter here will
    # over-ride the ones given in cmd_arguments because
    # traceroute will use the last one in the argument list.

    if method == "tcp":
        cmd_arguments.append('-T')
    elif method == "udp":
        cmd_arguments.append('-U')
    elif method == "icmp":
        cmd_arguments.append('-I')

    cmd = ['traceroute'] + cmd_arguments + [url]
    caller = command.Command(cmd, _traceroute_callback)
    caller.start()
    if not caller.started:
        message = ""
        if caller.exception is not None:
            if "No such file or directory" in caller.exception:
                message = ": traceroute not found or not installed"
            else:
                message = (", traceroute thread threw an exception: " +
                       str(caller.exception))
        if "enough privileges" in caller.notifications:
            message = ": not enough privileges"
        if "service not known" in caller.notifications:
            message = ": name or service not known"
        raise Exception("traceroute failed to start" + message)

    # check every 5 seconds to see if the execution has stopped
    while caller.thread.isAlive():
        time.sleep(5)

    # parse the output
    # a healthy line should looks like this:
    # 1  10.0.1.1 (10.0.1.1)  0.675 ms  0.576 ms  0.533 ms
    #
    # an empty output looks like this:
    # 2 * * *

    hops = {}
    meaningful_hops = 0
    total_hops = 0

    lines = caller.notifications.split("\n")
    for line in lines:
        line = line.split()
        try:
            # if the first value is not a number, just pass
            int(line[0])
        except:
            continue

        total_hops = total_hops + 1
        if len(line) == 9:
            number, domain_name, ip, rtt1, ms, rtt2, ms, rtt3, ms = line
            # remove parentheses from around the ip address
            ip = ip[1:-1]
            number = int(number)
            # sometimes, some RTT values are not present and there is
            # an asterisk in their place.
            # this should be handled by the whoever analyses the
            # output.
            hops[number] = { "domain_name" : domain_name,
                             "ip"          : ip,
                             "rtt1"        : rtt1,
                             "rtt2"        : rtt2,
                             "rtt3"        : rtt3
                           }
            meaningful_hops = meaningful_hops + 1
        elif len(line) == 4:
            number, asterisk, asterisk, asterisk = line
            number = int(number)
            hops[number] = {}

    results = {}
    results["url"] = url
    results["total_hops"] = total_hops
    results["meaningful_hops"] = meaningful_hops
    results["hops"] = hops
    return results


def _traceroute_callback(self, line, kill_switch):
    """Callback function to handle traceroute.
    """

    line = line.lower()
    if "traceroute to" in line:
        self.started = True
    # need to run as root but not running as root.
    # usually happens when doing TCP traceroute.
    if "enough privileges" in line:
        self.error = True
        self.kill_switch()
        self.stopped = True
    # name resolution failed
    if "service not known" in line:
        self.error = True
        self.kill_switch()
        self.stopped = True
