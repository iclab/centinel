import os
import time
import json
import pickle
import socket
import logging
import requests
import subprocess
import multiprocessing as mp
from datetime import timedelta
from urlparse import urljoin

import country_module as convertor
import centinel.backend
import centinel.vpn.openvpn as openvpn

def retrieve_anchor_list(directory):
    """ Retrieve anchor lists with RIPE API
    """
    logging.info("Starting to fetch RIPE anchors")
    landmark_path = os.path.join(directory, "landmarks_list.pickle")
    if os.path.isfile(landmark_path):
        with open(landmark_path, "r") as f:
            json_data = pickle.load(f)
        if (time.time() - json_data['timestamp']) <= timedelta(days=30).total_seconds():
            return json_data['anchors']
    logging.info("landmarks_list pickle is not available or expired, starting to fetch it.")
    s_time = time.time()
    BASE_URL = 'https://atlas.ripe.net/api/v2'
    query_url = BASE_URL + '/anchors/'
    anchors = dict()
    while True:
        resp = requests.get(query_url)
        temp = resp.json()
        for this in temp['results']:
            assert this['geometry']['type'] == "Point"
            anchor_name = this['fqdn'].split('.')[0].strip()
            anchors[anchor_name] = {'aid': this["id"],
                                    'pid': this["probe"],
                                    'ip_v4': this["ip_v4"],
                                    'asn_v4': this["as_v4"],
                                    'longitude': this["geometry"]["coordinates"][0],
                                    'latitude': this["geometry"]["coordinates"][1],
                                    'country': this["country"],
                                    'city': this["city"]}
        next_url = temp.get("next")
        if next_url is None:
            break
        query_url = urljoin(query_url, next_url)
    ripe_anchors = {'timestamp': time.time(), 'anchors': anchors}
    with open(landmark_path, "w") as f:
        pickle.dump(ripe_anchors, f)
    e_time = time.time()
    logging.info("Finishing to fetch RIPE anchors (%s sec)" %(e_time-s_time))
    return anchors


def send_ping(param):
    this_host, ip = param
    logging.info("Pinging (%s, %s)" % (this_host, ip))
    times = dict()
    ping = subprocess.Popen(["ping", "-c", "10", "-i", "0.3", ip],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, error = ping.communicate()
    output = out.split('\n')
    this_delays = list()
    for i in output:
        try:
            this_delays.append(i.split('time=')[1])
        except:
            continue
    times[this_host] = this_delays
    return times


def perform_probe(sanity_directory, vpn_provider, target_ip, hostname, target_cnt, anchors):
    """Send ping 10 times to landmarks and choose the minimum
    :return: times [host] = list()
    """
    logging.info("Start Probing [%s(%s)]" %(hostname, target_ip))
    pickle_path = os.path.join(sanity_directory, 'pings/' + vpn_provider)
    if not os.path.exists(pickle_path):
        os.makedirs(pickle_path)
    times = dict()
    s_time = time.time()
    results = []
    process_num = 25
    pool = mp.Pool(processes=process_num)
    results.append(pool.map(send_ping, [(this_host, Param['ip_v4']) for this_host, Param in anchors.iteritems()]))
    _sum = 0
    _total = 0
    for output in results[0]:
        _total += 1
        for key, value in output.iteritems():
            _sum += len(value)
            if key not in times:
                times[key] = list()
            for this in value:
                times[key].append(this)
    e_time = time.time()
    logging.info("Finish Probing [%s(%s)]: average succeeded pings=%.2f/10 (%.2fsec)"
                 %(hostname, target_ip, _sum/float(_total), e_time - s_time))
    pool.close()
    pool.join()
    final = {hostname: {'pings': times, 'cnt': target_cnt, 'ip_v4': target_ip,
                        'timestamp': time.time(), 'vpn_provider': vpn_provider}}
    logging.info("Creating pickle file")
    with open(pickle_path+'/'+vpn_provider+'-'+hostname+'-'+target_ip+'-'+target_cnt+'.pickle', 'w') as f:
        pickle.dump(final, f)
        logging.info("Pickle file successfully created.")


def start_probe(conf_list, conf_dir, vpn_dir, auth_file, crt_file, tls_auth,
                key_direction, sanity_path, vpn_provider, anchors):
    """ Run vpn_walk to get pings from proxy to anchors
    """
    start_time = time.time()
    for filename in conf_list:
        centinel_config = os.path.join(conf_dir, filename)
        config = centinel.config.Configuration()
        config.parse_config(centinel_config)
        # get ip address of hostnames
        hostname = os.path.splitext(filename)[0]
        try:
            vp_ip = socket.gethostbyname(hostname)
        except Exception as exp:
            logging.exception("Failed to resolve %s : %s" % (hostname, str(exp)))
            continue
        # get country for this vpn
        with open(centinel_config) as fc:
            json_data = json.load(fc)
        country_in_config = ""
        if 'country' in json_data:
            country_in_config = json_data['country']
        if (len(country_in_config) > 2):
            country = convertor.country_to_a2(country_in_config)
        # start openvpn
        vpn_config = os.path.join(vpn_dir, filename)
        logging.info("%s: Starting VPN. (%s)" %(filename, country))
        vpn = openvpn.OpenVPN(timeout=60, auth_file=auth_file, config_file=vpn_config,
                              crt_file=crt_file, tls_auth=tls_auth, key_direction=key_direction)
        vpn.start()
        if not vpn.started:
            logging.error("%s: Failed to start VPN!" % filename)
            vpn.stop()
            time.sleep(5)
            continue
        # sending ping to the anchors
        try:
            perform_probe(sanity_path, vpn_provider, vp_ip, hostname, country, anchors)
        except:
            logging.warning("Failed to send pings from %s" % vp_ip)
        logging.info("%s: Stopping VPN." % filename)
        vpn.stop()
        time.sleep(5)
    end_time = time.time() - start_time
    logging.info("Finished all probing: %.2fsec" %(end_time))