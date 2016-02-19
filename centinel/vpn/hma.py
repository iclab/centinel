#!/usr/bin/python
# hma.py: collection of functions to create vpn config files from the
# Hide My Ass VPN service

import os
import requests
import sys


def create_config_files(directory):
    """Create all available VPN configuration files in the given directory

    Note: I am basically just following along with what their script
    client does

    """
    # get the config file template
    template_url = ("https://securenetconnection.com/vpnconfig/"
                    "openvpn-template.ovpn")
    resp = requests.get(template_url)
    resp.raise_for_status()
    template = resp.content

    # get the available servers and create a config file for each server
    server_url = ("https://securenetconnection.com/vpnconfig/"
                  "servers-cli.php")
    resp = requests.get(server_url)
    resp.raise_for_status()
    servers = resp.content.split("\n")

    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(os.path.join(directory, "servers.txt"), 'w') as f:
        f.write(resp.content)

    for server_line in servers:
        if server_line.strip() == "":
            continue
        server_line = server_line.split("|")
        try:
            ip, desc, country, udp_sup, tcp_sup = server_line
        except ValueError:
            ip, desc, country, udp_sup, tcp_sup, no_rand = server_line
        with open(os.path.join(directory, ip + ".ovpn"), 'w') as file_o:
            file_o.write(template)
            # create tcp if available, else udp
            tcp_sup = tcp_sup.strip()
            if tcp_sup:
                port, proto = 443, "tcp"
            else:
                port, proto = 53, "udp"
            file_o.write("remote {0} {1}\n".format(ip, port))
            file_o.write("proto {0}\n".format(proto))
            # add automatic dns server update
            file_o.write("up /etc/openvpn/update-resolv-conf\n")
            file_o.write("down /etc/openvpn/update-resolv-conf\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
