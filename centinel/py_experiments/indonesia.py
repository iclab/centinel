import os
import socket
import sys
import struct
import dns.resolver
import time
import urllib2
import subprocess

from scapy.all import *
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
        self.traceroute(result, self.host)
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

    def isIp(self, string):
        a = string.split('.')
        if len(a) != 4:
           return False
        for x in a:
            if not x.isdigit():
                return False
            i = int(x)
            if i < 0 or i > 255:
                return False
        return True
    
    def traceroute(self, results, dest_name):
        t = 1
        finalIp = "Placeholder"
        complete_traceroute = ""
        for t in range(1,30):
            
            print("Ttl: " + str(t))
            '''process = "ping " + dest_name + " -c 1 -t " + str(t)'''
            process = ['ping', dest_name, '-c 1', '-t ' + str(t)]
            response = subprocess.Popen(process, stdout=subprocess.PIPE).communicate()[0]
            if t == 1:
                pingSendInfo = response.splitlines()[0]
                pingSendSplit = pingSendInfo.split()
                finalIp = pingSendSplit[2].translate(None, '()')
                print("Final Ip: " + finalIp)
                
            ping_info = response.splitlines()[1]
            split_by_word = str.split(ping_info)
            reverseDns = "Not Found"
            ip = "Not Found";
            for string in split_by_word:
                stripped = string.translate(None, '():')
                if self.isIp(stripped):
                    ip = stripped
                if not '=' in stripped and '.' in stripped and not self.isIp(stripped):
                    reverseDns = stripped
            print("Reverse Dns: " + reverseDns)
            print("Ip Address: " + ip)
	    results["Hop" + str(t) + "Ip"] = ip
	    results["Hop" + str(t) + "ReverseDns"] = reverseDns
            complete_traceroute += ip + "|||" + reverseDns
            if ip == "Not Found" and reverseDns != "Not Found":
                pass
            if ip == finalIp:
                print("Finished Traceroute")
                break
            else:
                complete_traceroute += "->"
        results["Hops"] = t
        results["traceroute"] = complete_traceroute
	print("\nComplete Traceroute: " + complete_traceroute)
            

'''
    def traceroute(self, results, dest_name):
        host = dest_name
        ttl=1
        port=1001
        for ttl in range(1, 10):
            s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))
            s.settimeout(2)
            try:
                s.connect((host, port))
            except (socket.error, socket.timeout), err:
                print 'ttl=%02d: %s' % (ttl, err)
                print dest_name
                s.close()
                continue
            except KeyboardInterrupt:
                print 'ttl=%02d (KeyboardInterrupt)' % ttl
                break
            print 'ttl=%02d: OK' % (ttl)
            break
'''
