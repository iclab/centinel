import httplib2
import os
import sys
import urllib
import logging
from BeautifulSoup import BeautifulSoup, SoupStrainer


def create_config_files(directory):
    """
    Initialize directory ready for vpn walker
    :param directory: the path where you want this to happen
    :return:
    """
    # Some constant strings
    crt_url = "http://www.ipvanish.com/software/configs/ca.ipvanish.com.crt"
    config_set_url = "http://www.ipvanish.com/software/configs/"

    config_urls = []
    # Getting all available config files on webpage
    http = httplib2.Http()
    status, response = http.request(config_set_url)
    for link in BeautifulSoup(response, parseOnlyThese=SoupStrainer('a')):
        if link.has_key('href') and link['href'].endswith('.ovpn'):
            config_urls.append(config_set_url + link['href'])

    if not os.path.exists(directory):
        os.makedirs(directory)

    # Download certificate and configs
    url_opener = urllib.URLopener()
    url_opener.retrieve(crt_url, os.path.join(directory, '../ca.ipvanish.com.crt'))
    logging.info("Starting to download IPVanish config files. This might take a while.")
    for ovpn_link in config_urls:
        filename = ovpn_link.split('/')[-1]
        file_path = os.path.join(directory, filename)
        url_opener.retrieve(ovpn_link, file_path)
        # add dns update options to each file
        with open(file_path, 'a') as f:
            f.write("up /etc/openvpn/update-resolv-conf\n")
            f.write("down /etc/openvpn/update-resolv-conf\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage {0} <directory to create VPNs in>".format(sys.argv[0])
        sys.exit(1)
    create_config_files(sys.argv[1])
