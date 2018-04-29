#-c /home/katja/project/new_centinel/centinel/vpn_configs/expressvpn --create-expressvpn-configs
import os
import shutil
import logging
import hashlib
import pickle

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

def create_config_files(directory):
    """
    Initialize directory ready for vpn walker
    :param directory: the path where you want this to happen
    :return:
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

    #TODO: write a code to download credentials and config files from its site
    orig_path = '/nfs/london/data2/shicho/proxy-configs-2018/ovpn.tbear-split'
    server_country = {}
    config_dict = {}
    for filename in os.listdir(orig_path):
        if filename.endswith('.ovpn'):
            country = filename.split('-')[1]
        file_path = os.path.join(orig_path, filename)
        lines = [line.rstrip('\n') for line in open(file_path)]

        hostname = ""
        for line in lines:
            if line.startswith('remote'):
                hostname = line.split(' ')[1]
        if len(hostname) > 0:
            new_path = os.path.join(directory, hostname + '.ovpn')
            shutil.copyfile(file_path, new_path)
            server_country[hostname] = country

    # add dns server
    logging.info("Appending DNS update options")
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        with open(file_path, 'a') as f:
            f.write('\n')
            f.write('up /etc/openvpn/update-resolv-conf\n')
            f.write('down /etc/openvpn/update-resolv-conf\n')
        message = hash_file(file_path)
        config_dict[filename] = message
    output = open(os.path.join(directory, '../config_hash.pkl'), 'wb')
    pickle.dump(config_dict, output)
    output.close()

    print os.path.join(directory, 'servers.txt'), len(server_country)
    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
        for hostname in server_country:
            f.write('|'.join([hostname, server_country[hostname]]) + '\n')
