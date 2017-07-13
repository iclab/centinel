import os
import sys
import csv
import logging
import pickle
import time
import subprocess
import multiprocessing as mp
import numpy as np
from urllib import urlopen
from bs4 import BeautifulSoup
from geopy.distance import vincenty
from geopy.geocoders import Nominatim

#-d vpn_providers/ipvanish/ -u auth_file --crt-file ca.ipvanish.com.crt


def get_anchor_list(directory):
    """Get a list of all RIPE Anchors
    :return: anchors [hostname]:dict()  "probe"
                                        "city"
                                        "country"
                                        "ip"
                                        "asn"
    """
    logging.info("Starting to fetch RIPE anchors")
    landmark_path = os.path.join(directory,"landmarks_list.pickle")
    try:
        with open(landmark_path, "r") as f:
            anchors = pickle.load(f)
        return anchors

    except:
        try:
            # sys.stderr.write("Retrieving landmark list...")
            logging.info("landmarks_list pickle is not available, starting to fetch it")
            anchors = dict()
            try:
                ## you can get "RIPE_anchor_list.csv" by crawling RIPE first page of anchors (table)
                ripe_path = os.path.join(directory,'RIPE_anchor_list.csv')
                with open(ripe_path, "r") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row[0] == 'Hostname':
                            continue
                        anchors[row[0]] = {'probe': row[1], 'city': row[3], 'country': row[4], 'ip': str(), 'asn': str()}
            except:
                logging.info("RIPE_anchor list is not available, starting to fetch it")
                # parsing ripe anchor website
                reload(sys)
                sys.setdefaultencoding('utf-8')


                html = urlopen('https://atlas.ripe.net/anchors/list/').read()
                soup = BeautifulSoup(html,"html.parser")
                ripe_records = (soup.find_all('tr'))
                all_records = []
                for record in ripe_records:
                    columns = record.find_all('td')
                    rec = []
                    for column in columns:
                        soup_column = BeautifulSoup(str(column),"html.parser")
                        rec.append('\"' + soup_column.td.text.strip().replace('\n','') + '\"')
                    if(len(rec) > 0):
                        all_records.append(rec)
                ripe_path = os.path.join(directory,'RIPE_anchor_list.csv')
                with open(ripe_path,'w') as f:
                    f.write('Hostname,Probe,Company,City,Country,Capabilities\n')
                    for sublist in all_records:
                        for item in sublist:
                            f.write(item + ',')
                        f.write('\n')
    		logging.info("Creating RIPE_anchor list")
                with open(ripe_path, "r") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row[0] == 'Hostname':
                            continue
                        anchors[row[0]] = {'probe': row[1], 'city': row[3], 'country': row[4], 'ip': str(), 'asn': str()}


            logging.info("Finished extracting RIPE anchors from file.")
            count = 0
            for key, value in anchors.iteritems():
                count += 1
                logging.info("Retrieving anchor %s, %s/%s" % (value['probe'], count, len(anchors)))
                url = 'https://atlas.ripe.net/probes/' + str(value['probe']) + '/#!tab-network/'
		try:
		        html = urlopen(url).read()
		        soup = BeautifulSoup(html,"html.parser")
		        for script in soup(["script", "style"]):
		            script.extract()
		        text = soup.get_text()
		        lines = (line.strip() for line in text.splitlines())
		        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
		        text = '\n'.join(chunk for chunk in chunks if chunk)
		        s_text = text.encode('utf-8').split('\n')
		        index = s_text.index("Internet Address")
		        anchors[key]['ip'] = str(s_text[index+1])
		        anchors[key]['asn'] = str(s_text[s_text.index("ASN")+1])
		except:
			logging.exception("Connection reset by Peer on %s" % (url))
            with open(landmark_path, "w") as f:
                pickle.dump(anchors, f)
            return anchors
        except (TypeError, ValueError, UnicodeError) as e:
            sys.exit(1)



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


def perform_probe(sanity_directory,vpn_provider, target_name, target_cnt, anchors):
    """Send ping 10 times to landmarks and choose the minimum
    :return: times [host] = list()
    """
    logging.info("Start Probing")

    pickle_path = os.path.join(sanity_directory,'pickle')
    if not os.path.exists(pickle_path):
        os.makedirs(pickle_path)

    times = dict()
    s_time = time.time()
    results = []
    process_num = 6
    pool = mp.Pool(processes=process_num)
    results.append(pool.map(send_ping, [(this_host, Param['ip']) for this_host, Param in anchors.iteritems()]))
    for output in results[0]:
        for key, value in output.iteritems():
            if key not in times:
                times[key] = list()
            for this in value:
                times[key].append(this)
    e_time = time.time()
    logging.info(e_time - s_time)
    pool.close()
    pool.join()
    final = {target_name: dict()}
    final[target_name]['pings'] = times
    final[target_name]['cnt'] = target_cnt
    logging.info("Creating pickle file")
    # putting time as a part of the filename
    time_unique = time.time()
    with open(pickle_path + '/' + target_name + '-' + target_cnt + '-' + str(time_unique) + '.pickle', 'w') as f:
        pickle.dump(final, f)
    	logging.info("Pickle file successfully created.")
    return final
