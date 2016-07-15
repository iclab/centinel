import StringIO
import csv
import logging
import os
import requests
import sys
from base64 import b64decode


def create_config_files(directory):
    """
    Initialize directory ready for vpn walker
    :param directory: the path where you want this to happen
    :return:
    """
    # Some constant strings
    vpn_gate_url = "http://www.vpngate.net/api/iphone/"

    if not os.path.exists(directory):
        os.makedirs(directory)

    # get csv into memory
    csv_str = ""
    logging.info("Downloading info from VPN Gate API...")
    r = requests.get(vpn_gate_url)
    for line in r.text.split('\n'):
        csv_str += line.encode('utf-8')
        csv_str += "\n"

    # convert csv string to string IO
    f = StringIO.StringIO(csv_str)

    # generate vpn dict
    vpn_dict = {}
    reader = csv.reader(f)
    reader.next()
    reader.next()
    for row in reader:
        if len(row) == 15:
            alpha2 = row[6]
            vpn_dict[alpha2] = vpn_dict.get(alpha2, [])
            vpn_dict[alpha2].append({
                "vpn_name": row[0],
                "ip": row[1],
                "country_name": row[5],
                "alpha2": alpha2,
                "openvpn_config": b64decode(row[-1])
            })
    f.close()

    server_country = {}

    # write config files
    for country in vpn_dict:
        for data in vpn_dict[country]:
            config_filename = "{}.ovpn".format(data['ip'])
            file_path = os.path.join(directory, config_filename)
            with open(file_path, 'w') as f:
                f.write(data['openvpn_config'])
                f.write("up /etc/openvpn/update-resolv-conf\n")
                f.write("down /etc/openvpn/update-resolv-conf\n")

            server_country[data['ip']] = country

    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
        for ip in server_country:
            f.write('|'.join([ip, server_country[ip]]) + '\n')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
