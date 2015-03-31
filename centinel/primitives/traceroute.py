#
# Abbas Razaghpanah (arazaghpanah@cs.stonybrook.edu)
# February 2015, Stony Brook University
#
# tracerout.py: interface to system traceroute
# for this to work, traceroute has to be installed
# and accessible.

import threading
import time

from centinel import command


def traceroute(domain, method="udp", cmd_arguments=None, external=None):
    """This function uses centinel.command to issue
    a traceroute command, wait for it to finish execution and
    parse the results out to a dictionary.

    Params:
    domain-        the domain to be queried
    method-        the packet type used for traceroute, ICMP by default
    cmd_arguments- the list of arguments that need to be passed
                   to traceroute.

    """

    # the method specified by the function parameter here will
    # over-ride the ones given in cmd_arguments because
    # traceroute will use the last one in the argument list.

    if cmd_arguments is None:
        cmd_arguments = []

    if method == "tcp":
        cmd_arguments.append('-T')
    elif method == "udp":
        cmd_arguments.append('-U')
    elif method == "icmp":
        cmd_arguments.append('-I')

    cmd = ['traceroute'] + cmd_arguments + [domain]
    caller = command.Command(cmd, _traceroute_callback)
    caller.start()
    if not caller.started:
        message = ""
        if caller.exception is not None:
            if "No such file or directory" in caller.exception:
                message = ": traceroute not found or not installed"
            else:
                message = (", traceroute thread threw an "
                           "exception: %s" (caller.exception))
        if "enough privileges" in caller.notifications:
            message = ": not enough privileges"
        if "service not known" in caller.notifications:
            message = ": name or service not known"
        results = {}
        results["domain"] = domain
        results["method"] = method
        results["error"] = message
        if external is not None and type(external) is dict:
            external[domain] = results
        return results

    forcefully_terminated = False
    timeout = 60
    start_time = time.time()
    # check every second to see if the execution has stopped
    while caller.thread.isAlive():
        if (time.time() - start_time) > timeout:
            caller.stop()
            forcefully_terminated = True
            break
        time.sleep(1)
    # we are only accurate down to seconds, so we have
    # to round up
    time_elapsed = int(time.time() - start_time)

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
    line_number = 0
    unparseable_lines = {}
    for original_line in lines:
        line_number = line_number + 1
        if original_line == "":
            continue
        line = original_line.split()
        if len(line) == 9:
            total_hops = total_hops + 1
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
        else:
            number = line[0]
            try:
                number = int(number)
                total_hops = total_hops + 1
                hops[number] = { "raw" : original_line }
            except ValueError:
                unparseable_lines[line_number] = original_line
    results = {}
    results["domain"] = domain
    results["method"] = method
    results["total_hops"] = total_hops
    results["meaningful_hops"] = meaningful_hops
    results["hops"] = hops
    results["unparseable_lines"] = unparseable_lines
    results["forcefully_terminated"] = forcefully_terminated
    results["time_elapsed"] = time_elapsed
    # the external result is used when threading to store
    # the results in the list container provided.
    if external is not None and type(external) is dict:
        external[domain] = results

    return results


def traceroute_batch(input_list, method="udp", cmd_arguments=[],
                     delay_time=0.1, max_threads=100):
    """
    This is a parallel version of the traceroute primitive.

    Params:
    input_list-    the input is a list of domain names
    method-        the packet type used for traceroute, ICMP by default
    cmd_arguments- the list of arguments that need to be passed
                   to traceroute.
    delay_time-    delay before starting each thread
    max_threads-   maximum number of concurrent threads

    """
    results = {}
    threads = []
    thread_error = False
    thread_wait_timeout = 200
    for domain in input_list:
        wait_time = 0
        while threading.active_count() > max_threads:
            time.sleep(1)
            wait_time += 1
            if wait_time > thread_wait_timeout:
                thread_error = True
                break

        if thread_error:
            results["error"] = "Threads took too long to finish."
            break

        # add just a little bit of delay before starting the thread
        # to avoid overwhelming the connection.
        time.sleep(delay_time)

        thread = threading.Thread(target=traceroute,
                                  args=(domain, method, cmd_arguments,
                                        results))
        thread.setDaemon(1)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join(thread_wait_timeout)

    return results

def _traceroute_callback(self, line, kill_switch):
    """Callback function to handle traceroute.
    """

    line = line.lower()
    if "traceroute to" in line:
        self.started = True
    # need to run as root but not running as root.
    # usually happens when doing TCP and ICMP traceroute.
    if "enough privileges" in line:
        self.error = True
        self.kill_switch()
        self.stopped = True
    # name resolution failed
    if "service not known" in line:
        self.error = True
        self.kill_switch()
        self.stopped = True
