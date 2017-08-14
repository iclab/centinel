import httplib2
import logging
import os
import shutil
import socket
import sys
import urllib
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
    if not os.path.exists(updated_vpn_path):
	os.makedirs(updated_vpn_path)

    logging.info("Update Ipvanish Configs")
    
    # read python dict back from file
    pkl_file = open(os.path.join(directory, '../config_hash.pkl'), 'rb')
    old_config_dict = pickle.load(pkl_file)
    pkl_file.close()


    config_zip_url = "http://www.ipvanish.com/software/configs/configs.zip"

    logging.info("Starting to download IPVanish config file zip")

    zip_response = urllib2.urlopen(config_zip_url)
    zip_content = zip_response.read()
    zip_path = os.path.join(directory, '../configs.zip')
    unzip_path = os.path.join(directory, '../unzipped')

    if not os.path.exists(unzip_path):
        os.makedirs(unzip_path)
    with open(zip_path, 'w') as f:
	f.write(zip_content)

    logging.info("Extracting zip file")
    unzip(zip_path, unzip_path)


    # remove zip file
    os.remove(zip_path)
    
    server_country = {}
    new_config_dict = {}

    for filename in os.listdir(unzip_path):
        if filename.endswith('.ovpn'):
            country = filename.split('-')[1]

            file_path = os.path.join(unzip_path, filename)
            lines = [line.rstrip('\n') for line in open(file_path)]

            # get ip address for this vpn
            hostname = ""
            for line in lines:
                if line.startswith('remote'):
                    hostname = line.split(' ')[1]
            if len(hostname) > 0:
                new_path = os.path.join(updated_vpn_path, hostname + '.ovpn')
                shutil.copyfile(file_path, new_path)
                server_country[hostname] = country
            else:
                logging.warn("Unable to resolve hostname and remove %s" % filename)
                os.remove(file_path)

    for filename in os.listdir(updated_vpn_path):
	file_path = os.path.join(updated_vpn_path, filename)
	message = hash_file(file_path)
	# print(filename, message)
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
		    update_list.append(vp)
		else:
		    continue
	if found_vpn_flag == 0:
	    delete_list.append(vp)
    # new additions
    add_list = []
    add_list.extend((set(new_config_dict.keys()) - set(old_config_dict.keys())))
    print('vp\'s to be added: ', add_list)
    print('vp\'s tp be deleted: ', delete_list)
    print('vp\'s to be updated: ', update_list)

    output = open(os.path.join(directory, '../config_hash.pkl'), 'wb')
    pickle.dump(new_config_dict, output)
    output.close()

    print os.path.join(directory, 'servers.txt'), len(server_country)
    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
        for hostname in server_country:
            f.write('|'.join([hostname, server_country[hostname]]) + '\n')

    # remove extracted folder
    shutil.rmtree(unzip_path)


    return [delete_list, update_list, add_list]


def create_config_files(directory):
    """
    Initialize directory ready for vpn walker
    :param directory: the path where you want this to happen
    :return:
    """
    # Some constant strings
    config_zip_url = "http://www.ipvanish.com/software/configs/configs.zip"

    if not os.path.exists(directory):
        os.makedirs(directory)

    logging.info("Starting to download IPVanish config file zip")
    zip_response = urllib2.urlopen(config_zip_url)
    zip_content = zip_response.read()
    zip_path = os.path.join(directory, '../configs.zip')
    unzip_path = os.path.join(directory, '../unzipped')

    if not os.path.exists(unzip_path):
        os.makedirs(unzip_path)
    with open(zip_path, 'w') as f:
	f.write(zip_content)

    logging.info("Extracting zip file")
    unzip(zip_path, unzip_path)

    # remove zip file
    os.remove(zip_path)

    # copy ca and key to root path
    shutil.copyfile(os.path.join(unzip_path, 'ca.ipvanish.com.crt'),
                    os.path.join(directory, '../ca.ipvanish.com.crt'))

    # move all config files to /vpns
    config_dict = {}
    server_country = {}
    for filename in os.listdir(unzip_path):
        if filename.endswith('.ovpn'):
            country = filename.split('-')[1]

            file_path = os.path.join(unzip_path, filename)
            lines = [line.rstrip('\n') for line in open(file_path)]

            # get ip address for this vpn
            hostname = ""
            for line in lines:
                if line.startswith('remote'):
                    hostname = line.split(' ')[1]
                    # added because gethostbyname will fail on some hostnames
                    # try:
                    # ip = socket.gethostbyname(hostname)
                    # break
                    # except socket.gaierror:
                    #    logging.exception("Failed to resolve %s" %hostname)
                    # continue

            if len(hostname) > 0:
                new_path = os.path.join(directory, hostname + '.ovpn')
                shutil.copyfile(file_path, new_path)
                server_country[hostname] = country
            else:
                logging.warn("Unable to resolve hostname and remove %s" % filename)
                os.remove(file_path)

    # writing pickle file of ovpn configs
    for filename in os.listdir(directory):
	file_path = os.path.join(directory, filename)
	message = hash_file(file_path)
	# print filename, message
	config_dict[filename] = message

    output = open(os.path.join(directory, '../config_hash.pkl'), 'wb')
    pickle.dump(config_dict, output)
    output.close()
    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
        for hostname in server_country:
            f.write('|'.join([hostname, server_country[hostname]]) + '\n')

    # remove extracted folder
    shutil.rmtree(unzip_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
