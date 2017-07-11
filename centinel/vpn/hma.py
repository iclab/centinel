#!/usr/bin/python
# hma.py: collection of functions to create vpn config files from the
# Hide My Ass VPN service

import os
import requests
import sys
import shutil
import logging
import socket
import zipfile
import urllib2

def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
	zf.extractall(dest_dir)
	
def create_config_files(directory):
    """
    Initialize directory ready for vpn walker
    :param directory: the path where you want this to happen
    :return:
    """
    config_zip_url = "https://hidemyass.com/vpn-config/vpn-configs.zip"
    
    if not os.path.exists(directory):
	os.makedirs(directory)
	
    logging.info("Starting to download hma config file zip")
    
    zip_response = urllib2.urlopen(config_zip_url)
    zip_content = zip_response.read()
    zip_path = os.path.join(directory, '../vpn-configs.zip')

    with open(zip_path,'w') as f:
	f.write(zip_content)
    logging.info("Extracting zip file")
    unzip(zip_path, os.path.join(directory, '../'))
    
    ca_url = "https://vpn.hidemyass.com/vpn-config/keys/ca.crt"
    hmauserauth_url = "https://vpn.hidemyass.com/vpn-config/keys/hmauser.crt"
    hmauserkey_url = "https://vpn.hidemyass.com/vpn-config/keys/hmauser.key"
    
    ca_response = urllib2.urlopen(ca_url)
    ca_content = ca_response.read()
    with open(os.path.join(directory, '../ca.crt'), 'w') as f:
	f.write(ca_content)

    response_userauth = urllib2.urlopen(hmauserauth_url)
    userauth_content = response_userauth.read()
    with open(os.path.join(directory, '../hmauser.key'), 'w') as f:
	f.write(userauth_content)

    response_userkey = urllib2.urlopen(hmauserkey_url)
    userkey_content = response_userkey.read()
    with open(os.path.join(directory, '../hmauser.key'), 'w') as f:
	f.write(userkey_content)
	
    # remove zip file
    os.remove(zip_path)
    

    # move all config files to /vpns
    orig_path = os.path.join(directory, '../TCP')
    
    server_country = {}
    for filename in os.listdir(orig_path):
	if filename.endswith('.ovpn'):
	    country = filename.split('.')[0]
	file_path = os.path.join(orig_path, filename)
	lines = [line.rstrip('\n') for line in open(file_path)]
	
	ip = ""
	for line in lines:
	    if line.startswith('remote'):
		hostname = line.split(' ')[1]
		try:
		    ip = socket.gethostbyname(hostname)
		    break
		except socket.gaierror:
		    logging.info("Failed to resolve %s" %hostname)
		    continue
	if len(ip) > 0:
	    new_path = os.path.join(directory, ip + '.ovpn')
	    shutil.copyfile(file_path, new_path)
	    server_country[ip] = country

    # remove extracted folder
    shutil.rmtree(os.path.join(directory, '../TCP'))
    shutil.rmtree(os.path.join(directory, '../UDP'))
    
    # add dns update options to each file
    logging.info("Appending DNS update options")
    for filename in os.listdir(directory):
	file_path = os.path.join(directory, filename)
	with open(file_path, 'a') as f:
	    f.write('\n')
	    f.write('up /etc/openvpn/update-resolv-conf\n')
	    f.write('down /etc/openvpn/update-resolv-conf\n')
	    

    print os.path.join(directory, 'servers.txt'), len(server_country)
    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
	for ip in server_country:
	    f.write('|'.join([ip, server_country[ip]]) + '\n')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
