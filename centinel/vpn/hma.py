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
import pickle
import hashlib

def hash_file(filename):
   """
   This function returns the SHA-1 hash
   of the file passed into it
   """

   # make a hash object
   h = hashlib.sha1()

   # open file for reading in binary mode
   with open(filename,'rb') as file:

       # loop till the end of the file
       chunk = 0
       while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)

   # return the hex representation of digest
   return h.hexdigest()


def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
	zf.extractall(dest_dir)


def update_config_files(directory):
    """
    Update directory for vpn walker
    :param directory:
    :return a list of delete, update and added vps:
    """
    updated_vpn_path = os.path.join(directory, '../updated_vpns')
    print(updated_vpn_path)
    if not os.path.exists(updated_vpn_path):
	os.makedirs(updated_vpn_path)

    logging.info("Update HMA Configs")

    # read python dict back from the file
    pkl_file = open(os.path.join(directory,'../config_hash.pkl'), 'rb')
    old_config_dict = pickle.load(pkl_file)
    pkl_file.close()

    config_zip_url = "https://hidemyass.com/vpn-config/vpn-configs.zip"

    logging.info("Starting to download hma config file zip")

    zip_response = urllib2.urlopen(config_zip_url)
    zip_content = zip_response.read()
    zip_path = os.path.join(directory, '../vpn-configs.zip')

    with open(zip_path,'w') as f:
	f.write(zip_content)
    logging.info("Extracting zip file")
    unzip(zip_path, os.path.join(directory, '../'))

    # remove zip file
    os.remove(zip_path)

    server_country = {}
    new_config_dict = {}


    orig_path = os.path.join(directory, '../TCP')
    config_dict = {}
    server_country = {}
    for filename in os.listdir(orig_path):
	if filename.endswith('.ovpn'):
	    country = filename.split('.')[0]
	file_path = os.path.join(orig_path, filename)
	lines = [line.rstrip('\n') for line in open(file_path)]

	hostname = ""
	for line in lines:
	    if line.startswith('remote'):
		hostname = line.split(' ')[1]
	if len(hostname) > 0:
	    new_path = os.path.join(updated_vpn_path, hostname + '.ovpn')
	    shutil.copyfile(file_path, new_path)
	    server_country[hostname] = country

    # remove extracted folder
    shutil.rmtree(os.path.join(directory, '../TCP'))
    shutil.rmtree(os.path.join(directory, '../UDP'))

    # add dns update options to each file
    logging.info("Appending DNS update options")
    for filename in os.listdir(updated_vpn_path):
	file_path = os.path.join(updated_vpn_path, filename)
	with open(file_path, 'a') as f:
	    f.write('\n')
	    f.write('up /etc/openvpn/update-resolv-conf\n')
	    f.write('down /etc/openvpn/update-resolv-conf\n')
	message = hash_file(file_path)
	new_config_dict[filename] = message

    delete_list = []
    update_list = []
    # delete and update
    for vp in old_config_dict:
        found_vpn_flag = 0
	for newvp in new_config_dict:
	    if(vp == newvp):
		found_vpn_flag = 1
		if(old_config_dict[vp] != new_config_dict[newvp]):
#		    print('vpn update'+ str(vp))
		    update_list.append(vp)
		else:
#		    print('no update needed')
		    continue
        if found_vpn_flag == 0:
	    delete_list.append(vp)
    # new additions
    add_list = []
    add_list.extend((set(new_config_dict.keys()) - set(old_config_dict.keys())))
    print('vp\'s to be added: ' , add_list)	
    print('vp\'s to be deleted: ' , delete_list)
    print('vp\'s to be updated: ', update_list)
	    
#    print(new_config_dict)
    output = open(os.path.join(directory, '../config_hash.pkl'), 'wb')
    pickle.dump(new_config_dict, output)
    output.close()
    
    
    print os.path.join(directory, 'servers.txt'), len(server_country)
    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
	for hostname in server_country:
	    f.write('|'.join([hostname, server_country[hostname]]) + '\n')

   
    return [delete_list, update_list, add_list]


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
    config_dict = {}
    server_country = {}
    for filename in os.listdir(orig_path):
	if filename.endswith('.ovpn'):
	    country = filename.split('.')[0]
	file_path = os.path.join(orig_path, filename)
	lines = [line.rstrip('\n') for line in open(file_path)]
	
	hostname = ""
	for line in lines:
	    if line.startswith('remote'):
		hostname = line.split(' ')[1]
		# try:
		#     ip = socket.gethostbyname(hostname)
		#     break
		# except socket.gaierror:
		#     logging.exception("Failed to resolve %s" %hostname)
		#     continue
	if len(hostname) > 0:
	    new_path = os.path.join(directory, hostname + '.ovpn')
	    shutil.copyfile(file_path, new_path)
	    server_country[hostname] = country

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
    # print(config_dict)
	message = hash_file(file_path)
	config_dict[filename] = message
    output = open(os.path.join(directory, '../config_hash.pkl'), 'wb')
    pickle.dump(config_dict, output)
    output.close()


    print os.path.join(directory, 'servers.txt'), len(server_country)
    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
	for hostname in server_country:
	    f.write('|'.join([hostname, server_country[hostname]]) + '\n')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
