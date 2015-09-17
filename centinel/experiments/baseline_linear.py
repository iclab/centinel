#
# Abbas Razaghpanah (arazaghpanah@cs.stonybrook.edu)
# February 2015, Stony Brook University
#
# baseline_linear.py: baseline experiment that runs through
# lists of URLs and does HTTP + DNS + traceroute for
# every URL in the list.
#
# Input files can be either simple URL lists or CSV
# files. In case of CSV input, the first column is
# assumed to be the URL and the rest of the columns
# are included in the results as metadata.


import csv
import logging
import os
import time
import urlparse

from centinel.experiment import Experiment
from centinel.primitives import dnslib
from centinel.primitives.tcpdump import Tcpdump
from centinel.primitives import tls
import centinel.primitives.http as http
import centinel.primitives.traceroute as traceroute


class LinearBaselineExperiment(Experiment):
    name = "baseline_linear"
    # country-specific, world baseline
    # this can be overridden by the main thread
    input_files = ['country.csv', 'world.csv']

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

        if self.params is not None:
            # process parameters
            if "traceroute_methods" in self.params:
                self.traceroute_methods = self.params['traceroute_methods']

        if os.geteuid() != 0:
            logging.info("Centinel is not running as root, "
                         "traceroute will be limited to UDP.")
            # only change to udp if method list was not empty before
            if self.traceroute_methods:
                self.traceroute_methods = ["udp"]

    def run(self):
        if self.record_pcaps:
            self.external_results = {}

        for input_file in self.input_files.items():
            logging.info("Testing input file %s..." % (input_file[0]))
            self.results.append(self.run_file(input_file))

    def run_file(self, input_file):
        file_name, file_contents = input_file

        # Initialize the results for this input file.
        # This can be anything from file name to version
        # to any useful information.
        result = {'file_name': file_name}

        http_results = {}
        tls_results = {}
        dns_results = {}
        traceroute_results = {}
        url_metadata_results = {}
        file_metadata = {}
        file_comments = []

        # each pcap file is stored in a separate file
        # designated by a number. the indexes are stored
        # in the json file and the pcap files are stored
        # with their indexes as file names.
        pcap_results = {}
        pcap_indexes = {}
        url_index = 0
        index_row = None
        comments = ""

        # we may want to make this threaded and concurrent
        csvreader = csv.reader(file_contents, delimiter=',', quotechar='"')
        for row in csvreader:
            """
            First few lines are expected to be comments in key: value
            format. The first line after that could be our column header
            row, starting with "url", and the rest are data rows.
            This is a sample input file we're trying to parse:

            # comment: Global List,,,,,
            # date: 03-17-2015,,,,,
            # version: 1,,,,,
            # description: This is the global list. Last updated in 2012.,,,,
            url,country,category,description,rationale,provider
            http://8thstreetlatinas.com,glo,PORN,,,PRIV
            http://abpr2.railfan.net,glo,MISC,Pictures of trains,,PRIV

            """

            # parse file comments, if it looks like "key : value",
            # parse it as a key-value pair. otherwise, just
            # store it as a raw comment.
            if row[0][0] == '#':
                row = row[0][1:].strip()
                if len(row.split(':')) > 1:
                    key, value = row.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    file_metadata[key] = value
                else:
                    file_comments.append(row)
                continue

            # detect the header row and store it
            # it is usually the first row and starts with "url,"
            if row[0].strip().lower() == "url":
                index_row = row
                continue

            url = row[0].strip()
            if url is None:
                continue

            meta = row[1:]
            url_index = url_index + 1
            http_ssl = False
            ssl_port = 443
            http_path = '/'

            # parse the URL to extract netlocation, HTTP path, domain name,
            # and HTTP method (SSL or plain)
            try:
                urlparse_object = urlparse.urlparse(url)
                http_netloc = urlparse_object.netloc

                # if netloc is not urlparse-able, add // to the start
                # of URL
                if http_netloc == '':
                    urlparse_object = urlparse.urlparse('//%s' % (url))
                    http_netloc = urlparse_object.netloc

                domain_name = http_netloc.split(':')[0]

                http_path = urlparse_object.path
                if http_path == '':
                    http_path = '/'

                # we assume scheme is either empty, or "http", or "https"
                # other schemes (e.g. "ftp") are out of the scope of this
                # measuremnt
                if urlparse_object.scheme == "https":
                    http_ssl = True
                    if len(http_netloc.split(':')) == 2:
                        ssl_port = http_netloc.split(':')[1]

            except Exception as exp:
                logging.warning("%s: failed to parse URL: %s" % (url, exp))
                http_netloc = url
                http_ssl    = False
                ssl_port = 443
                http_path   = '/'
                domain_name = url

            # start tcpdump
            td = Tcpdump()
            tcpdump_started = False

            try:
                if self.record_pcaps:
                    td.start()
                    tcpdump_started = True
                    logging.info("%s: tcpdump started..." % (url))
                    # wait for tcpdump to initialize
                    time.sleep(1)
            except Exception as exp:
                logging.warning("%s: tcpdump failed: %s" % (url, exp))

            # HTTP GET
            logging.info("%s: HTTP" % (url))
            try:
                http_results[url] = http.get_request(http_netloc,
                                                     http_path,
                                                     ssl=http_ssl)
            except Exception as exp:
                logging.warning("%s: HTTP test failed: %s" % (url, exp))
                http_results[url] = {"exception": str(exp)}

            # TLS certificate
            # this will only work if the URL starts with https://
            if http_ssl:
                try:
                    tls_result = {}
                    logging.info("%s: TLS certificate" % (domain_name))
                    fingerprint, cert = tls.get_fingerprint(domain_name, ssl_port)
                    tls_result['port'] = ssl_port
                    tls_result['fingerprint'] = fingerprint
                    tls_result['cert'] = cert

                    tls_results[domain_name] = tls_result
                except Exception as exp:
                    logging.warning("%s: TLS certfiticate download failed: %s" %
                                    (domain_name, exp))
                    tls_results[domain_name] = {"exception": str(exp)}

            # DNS Lookup
            logging.info("%s: DNS" % (domain_name))
            try:
                dns_results[domain_name] = dnslib.lookup_domain(domain_name)
            except Exception as exp:
                logging.warning("%s: DNS lookup failed: %s" %
                                (domain_name, exp))
                dns_results[domain_name] = {"exception": str(exp)}

            # Traceroute
            for method in self.traceroute_methods:
                try:
                    logging.info("%s: Traceroute (%s)"
                                 % (domain_name, method.upper()))
                    traceroute_results[domain_name] = traceroute.traceroute(
                        domain_name, method=method)
                except Exception as exp:
                    logging.warning("%s: Traceroute (%s) failed: %s" %
                                    (domain_name, method.upper(), exp))
                    traceroute_results[domain_name] = {"exception": str(exp)}

            # end tcpdump
            if tcpdump_started:
                logging.info("%s: waiting for tcpdump..." % (url))
                # 2 seconds should be enough.
                time.sleep(2)
                td.stop()
                logging.info("%s: tcpdump stopped." % (url))
                pcap_indexes[url] = '%s-%s.pcap' % (file_name, format(url_index, '04'))
                pcap_results[pcap_indexes[url]] = td.pcap()

            # Meta-data
            url_metadata_results[url] = meta

        result["http"] = http_results
        result["tls"] = tls_results
        result["dns"] = dns_results
        result["traceroute"] = traceroute_results

        # if we have an index row, we should turn URL metadata
        # into dictionaries
        if index_row is not None:
            indexed_url_metadata = {}
            for url, meta in url_metadata_results.items():
                try:
                    indexed_meta = {}
                    for i in range(1, len(index_row)):
                        indexed_meta[index_row[i]] = meta[i - 1]
                    indexed_url_metadata[url] = indexed_meta
                except:
                    indexed_url_metadata[url] = indexed_meta
                    continue
            url_metadata_results = indexed_url_metadata

        result["url_metadata"] = url_metadata_results
        result["file_metadata"] = file_metadata
        result["file_comments"] = file_comments
        if self.record_pcaps:
            result['pcap_indexes'] = pcap_indexes
            self.external_results = dict(self.external_results.items() +
                                         pcap_results.items())

        return result
