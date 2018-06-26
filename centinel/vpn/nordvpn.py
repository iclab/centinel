import httplib2
import logging
import os
import shutil
import socket
import sys
import urllib
import zipfile


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
    config_zip_url = "https://downloads.nordcdn.com/configs/archives/servers/ovpn.zip"

    if not os.path.exists(directory):
        os.makedirs(directory)

    logging.info("Starting to download NordVPN config file zip")
    url_opener = urllib.URLopener()
    zip_path = os.path.join(directory, '../configs.zip')
    unzip_path = os.path.join(directory, '../unzipped')
    if not os.path.exists(unzip_path):
        os.makedirs(unzip_path)

    url_opener.retrieve(config_zip_url, zip_path)
    logging.info("Extracting zip file")
    unzip(zip_path, unzip_path)

    # remove zip file
    os.remove(zip_path)

    # move all config files to /vpns
    server_country = {}
    configs_path = os.path.join(unzip_path, 'ovpn_tcp')
    for filename in os.listdir(configs_path):
        if filename.endswith('.ovpn'):
            country = filename[0:2]

            file_path = os.path.join(configs_path, filename)
            lines = [line.rstrip('\n') for line in open(file_path)]

            # get ip address for this vpn
            ip = ""
            for line in lines:
                if line.startswith('remote'):
                    ip = line.split(' ')[1]
                    break

            if len(ip) > 0:
                new_path = os.path.join(directory, ip + '.ovpn')
                shutil.copyfile(file_path, new_path)
                server_country[ip] = country
            else:
                logging.warn("Unable to resolve hostname and remove %s" % filename)
                os.remove(file_path)

    with open(os.path.join(directory, 'servers.txt'), 'w') as f:
        for ip in server_country:
            f.write('|'.join([ip, server_country[ip]]) + '\n')

    # remove extracted folder
    shutil.rmtree(unzip_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
