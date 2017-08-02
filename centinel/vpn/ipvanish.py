import httplib2
import logging
import os
import shutil
import socket
import sys
import urllib
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
