#
# Abbas Razaghpanah (arazaghpanah@cs.stonybrook.edu)
# November 2016, Stony Brook University
#
# tcp_connect.py: TCP connect test

from datetime import datetime
import logging
import socket

def tcp_connect(host, port):
    result = {
        "host" : host,
        "port" : port
    }

    try:
        ip = socket.gethostbyname(host)
        if (ip is not None):
            result["ip"] = ip
    except Exception as err:
        result["ip_err"] = str(err)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(True)
        sock.settimeout(5)
        start_time = datetime.now()
        sock.connect((host, int(port)))
        end_time = datetime.now()
        elapsed = int((end_time - start_time).total_seconds() * 1000)
        sock.close()
        result["success"] = "true"
    except Exception as err:
        end_time = datetime.now()
        elapsed = int((end_time - start_time).total_seconds() * 1000)
        result["failure"] = str(err)


    logging.debug("time: " + str(elapsed) + "ms")
    result["time"] = str(elapsed)
    return result
