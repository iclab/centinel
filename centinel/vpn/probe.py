import os
import logging
import pickle
import time
import subprocess
import multiprocessing as mp
from datetime import timedelta
import requests
from urlparse import urljoin

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


def perform_probe(sanity_directory, vpn_provider, target_name, target_cnt, anchors):
    """Send ping 10 times to landmarks and choose the minimum
    :return: times [host] = list()
    """
    logging.info("Start Probing (%s)" %target_name)
    pickle_path = os.path.join(sanity_directory, 'pings')
    if not os.path.exists(pickle_path):
        os.makedirs(pickle_path)
    times = dict()
    s_time = time.time()
    results = []
    process_num = 25
    pool = mp.Pool(processes=process_num)
    results.append(pool.map(send_ping, [(this_host, Param['ip']) for this_host, Param in anchors.iteritems()]))
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
    logging.info("Finish Probing (%s): average %s/10 (%sec)" %(target_name, _sum/float(_total), e_time-s_time))
    pool.close()
    pool.join()
    final = {target_name: dict()}
    final[target_name]['pings'] = times
    final[target_name]['cnt'] = target_cnt
    logging.info("Creating pickle file")
    # putting time as a part of the filename
    time_unique = time.time()
    with open(pickle_path + '/' + vpn_provider + '-' + target_name + '-' + target_cnt + '-' + str(time_unique) + '.pickle', 'w') as f:
        pickle.dump(final, f)
        logging.info("Pickle file successfully created.")
    return final
