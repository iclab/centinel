#
# Abbas Razaghpanah (arazaghpanah@cs.stonybrook.edu)
# February 2015, Stony Brook University
#
# baseline.py: baseline experiment that runs through
# lists of URLs and does HTTP + DNS + traceroute for
# every URL in the list.
#
# Input files can be either simple URL lists or CSV
# files. In case of CSV input, the first column is
# assumed to be the URL and the rest of the columns
# are included in the results as metadata.


import os
import logging
import time
import urlparse

from centinel.experiment import Experiment
from centinel.primitives import dnslib
from centinel.primitives.tcpdump import Tcpdump
import centinel.primitives.http as http
import centinel.primitives.traceroute as traceroute


class BaselineExperiment(Experiment):
    name = "baseline"
    # country-specific, world baseline
    # this can be overridden by the main thread
    input_files = ['country', 'world']

    # we do our own tcpdump recording here
    overrides_tcpdump = True

    def __init__(self, input_files):
        self.input_files = input_files
        self.results = []

        # should we do tcpdump?
        if os.geteuid() != 0:
            self.record_pcaps = False
        else:
            self.record_pcaps = True

        if os.geteuid() != 0:
            logging.info("Centinel is not running as root, "
                         "traceroute will be limited to UDP.")
            self.traceroute_methods = ["udp"]
        else:
            self.traceroute_methods = ["icmp", "udp", "tcp"]

    def run(self):
        for input_file in self.input_files.items():
            logging.info("Testing input file %s..." % (input_file[0]))
            self.results.append(self.run_file(input_file))

    def run_file(self, input_file):
        file_name, file_contents = input_file

        # Initialize the results for this input file.
        # This can be anything from file name to version
        # to any useful information.
        result = {}
        result["file_name"] = file_name


        http_results = {}
        dns_results = {}
        traceroute_results = {}
        url_metadata_results = {}
        file_metadata = {}
        file_comments = []
        pcap_results = {}
        comments = ""
        # we may want to make this threaded and concurrent
        for line in file_contents:
            line = line.strip()

            # parse file comments, if it looks like "key : value",
            # parse it as a key-value pair. otherwise, just
            # store it as a raw comment.
            if line[0] == '#':
                line = line[1:].strip()
                if len(line.split(':')) > 1:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    file_metadata[key] = value
                else:
                    file_comments.append(line)
                continue

            url = line
            meta = ''

            # handle cases where URL is enclosed in quotes
            if line[0] == '"':
                next_quote = line[1:].find('"')
                url = line[1:next_quote + 1]
                # try to separate metadata, if any
                try:
                    meta = ','.join(line[next_quote + 2:].split(',')[1:])
                except:
                    pass

            # if the line doesn't start with a quote
            # but the list entry has comma separated meta-data
            elif len(line.split(',')) > 1:
                url, meta = line.split(',', 1)
                # remove trailing spaces
                url = url.strip()


            # parse the URL to extract netlocation, HTTP path, domain name,
            # and HTTP method (SSL or plain)
            try:
                http_netloc = ''.join(urlparse.urlparse(url).netloc)

                # if netloc is not urlparse-able, add // to the start
                # of URL
                if http_netloc == '':
                    url = '//' + url
                    http_netloc = ''.join(urlparse.urlparse(url).netloc)

                http_path = urlparse.urlparse(url).path
                if http_path == '':
                    http_path = '/'

                # we assume scheme is either empty, or "http", or "https"
                # other schemes (e.g. "ftp") are out of the scope of this
                # measuremnt
                http_ssl = False
                if urlparse.urlparse(url).scheme == "https":
                    http_ssl = True
            except Exception as exp:
                logging.warning("%s: failed to parse URL: %s" %(url, str(exp)))
                http_netloc = url
                http_ssl    = False
                http_path   = '/'

            domain_name = http_netloc.split(':')[0]

            # start tcpdump
            td = Tcpdump()
            tcpdump_started = False

            try:
                if self.record_pcaps:
                    td.start()
                    tcpdump_started = True
                    logging.info("%s: tcpdump started..." % (url))
                    # wait for tcpdump to initialize
                    time.sleep(2)
            except Exception as exp:
                logging.warning("%s: tcpdump failed: %s" %(url, str(exp)))

            # HTTP GET
            logging.info("%s: HTTP" % (url))
            try:
                http_results[url] = http.get_request(http_netloc,
                                                     http_path,
                                                     ssl=http_ssl)
            except Exception as exp:
                logging.info("%s: HTTP test failed: %s" %
                             (url, str(exp)))
                http_results[url] = { "exception" : str(exp) }

            # DNS Lookup
            logging.info("%s: DNS" % (domain_name))
            try:
                dns_results[domain_name] = dnslib.lookup_domain(domain_name)
            except Exception as exp:
                logging.info("%s: DNS lookup failed: %s" %
                             (domain_name, str(exp)))
                dns_results[domain_name] = { "exception" : str(exp) }

            # Traceroute
            for method in self.traceroute_methods:
                try:
                    logging.info("%s: Traceroute (%s)"
                                 % (domain_name, method.upper()))
                    traceroute_results[domain_name] = traceroute.traceroute(domain_name, method=method)
                except Exception as exp:
                    logging.info("%s: Traceroute (%s) failed: %s" %
                                    (domain_name, method.upper(), str(exp)))
                    traceroute_results[domain_name] = { "exception" : str(exp) }

            # end tcpdump
            if tcpdump_started:
                logging.info("%s: waiting for tcpdump..." %(url))
                # 2 seconds should be enough.
                time.sleep(2)
                td.stop()
                logging.info("%s: tcpdump stopped." %(url))

                pcap_results[url] = td.b64_output()

            # Meta-data

            # if meta is a pair of comma-separated values,
            # they should be treated as country and category
            if len(meta.strip().split(',')) == 2:
                country, category = meta.split(',')

                country = country.strip()
                category = category.strip()

                meta = { "country" : country,
                         "category" : category
                       }

            url_metadata_results[url] = meta

        result["http"] = http_results
        result["dns"] = dns_results
        result["traceroute"] = traceroute_results
        result["url_metadata"] = url_metadata_results
        result["file_metadata"] = file_metadata
        result["file_comments"] = file_comments
        if self.record_pcaps:
            result['pcap_results'] = pcap_results

        return result
