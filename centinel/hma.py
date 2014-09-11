#!/usr/bin/python
# Ben Jones bjones99@gatech.edu
# Georgia Tech Fall 2014
# Centinel project
#
# hma.py: collection of functions to create vpn config files from the
# Hide My Ass VPN service

import os
import os.path
import re
import requests
import sys


def create_config_files(directory):
    """Create all available VPN configuration files in the given directory

    Note: I am basically just following along with what their script
    client does

    """
    # get the config file template
    r = requests.get("https://securenetconnection.com/vpnconfig/"
                     "openvpn-template.ovpn")
    r.raise_for_status()
    template = r.content

    # get the available servers and create a config file for each server
    r = requests.get("https://securenetconnection.com/vpnconfig/"
                     "servers-cli.php")
    r.raise_for_status()
    servers = r.content.split("\n")

    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(os.path.join(directory, "servers.txt"), 'w') as f:
        f.write(r.content)

    for server_line in servers:
        if server_line.strip() == "":
            continue
        server_line = server_line.split("|")
        if len(server_line) == 5:
            ip, desc, country, udp_sup, tcp_sup = server_line
        else:
            ip, desc, country, udp_sup, tcp_sup, no_rand = server_line
        with open(os.path.join(directory, ip + ".ovpn"), 'w') as f:
            f.write(template)
            # create tcp if available, else udp
            if tcp_sup.strip() != "":
                port, proto = 443, "tcp"
            else:
                port, proto = 53, "udp"
            f.write("remote {0} {1}\n".format(ip, port))
            f.write("proto {0}\n".format(proto))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
