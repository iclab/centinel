import os
import socket
import sys
import struct
import dns.resolver
import time
import urllib2

from centinel.experiment_py import Experiment

class IndExperiment(Experiment):
    name = "indonesia"

    def __init__(self, input_file):
        self.input_file  = input_file
        self.results = []

    def run(self):
        for line in self.input_file:
            self.host = line.strip()
            self.ind_test()

    def ind_test(self):
        result = {"host " : self.host}
        self.dns_query(result, self.host)
        self.http_get(result, self.host)
        self.results.append(result)

    def http_get(self, results, dest_name):
        url = dest_name
        if not url.startswith("http://") or not url.startswith("https://"):
            url = "http://" + url
        start_time = time.time()
        contents = urllib2.urlopen(url)
        end_time = time.time()
        results["HttpTime"] = end_time - start_time
        results["Http"] = contents.read()
    
    def dns_query(self, results, dest_name):
        start_time = time.time()
        answers = dns.resolver.query(dest_name, 'A')
        end_time = time.time()
        results["DnsTime"] = end_time - start_time;
        results["DnsNumRecords"] = len(answers)
        n = 0
        for rdata in answers:
            results["A-record" + str(n)] = rdata.to_text()
            n += 1

        ''' print('got answers for ' + dest_name + ' in ' + str(end_time - start_time))'''


        
    def traceroute(self, dest_name):
        dest_addr = socket.gethostbyname(dest_name)
        port = 33434
        max_hops = 30
        icmp = socket.getprotobyname('icmp')
        udp = socket.getprotobyname('udp')
        ttl = 1
        
        while True:
            recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
            send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, udp)
            send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)

            # Build the GNU timeval struct (seconds, microseconds)
            timeout = struct.pack("ll", 5, 0)
        
            # Set the receive timeout so we behave more like regular traceroute
            recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeout)
        
            recv_socket.bind(("", port))
            sys.stdout.write(" %d  " % ttl)
            send_socket.sendto("", (dest_name, port))
            curr_addr = None
            curr_name = None
            finished = False
            tries = 3
            while not finished and tries > 0:
                try:
                    _, curr_addr = recv_socket.recvfrom(512)
                    finished = True
                    curr_addr = curr_addr[0]
                    try:
                        curr_name = socket.gethostbyaddr(curr_addr)[0]
                    except socket.error:
                        curr_name = curr_addr
                except socket.error as (errno, errmsg):
                    tries = tries - 1
                    sys.stdout.write("* ")
        
            send_socket.close()
            recv_socket.close()
        
            if not finished:
                pass
        
            if curr_addr is not None:
                curr_host = "%s (%s)" % (curr_name, curr_addr)
            else:
                curr_host = ""
            sys.stdout.write("%s\n" % (curr_host))

            ttl += 1
            if curr_addr == dest_addr or ttl > max_hops:
                break
