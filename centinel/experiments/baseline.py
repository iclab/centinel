#
# Abbas Razaghpanah (arazaghpanah@cs.stonybrook.edu)
# February 2015, Stony Brook University
#
# baseline.py: baseline experiment that runs through
# lists of URLs and does HTTP + DNS + traceroute for
# every URL in the list. This is done concurrently
# for each test.
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
from random import shuffle

import centinel.primitives.http as http
import centinel.primitives.traceroute as traceroute
from centinel.experiment import Experiment
from centinel.primitives import dnslib

try:
    from centinel.primitives import tcp_connect
except ImportError:
    # we should disable this if the primitive doesn't exist
    tcp_connect = None

from centinel.primitives import tls


class BaselineExperiment(Experiment):
    name = "baseline"
    # country-specific, world baseline
    # this can be overridden by the main thread
    input_files = ['country.csv', 'world.csv']
    tls_for_all = True

    def __init__(self, input_files):
        self.input_files = input_files
        self.results = []
        self.exclude_nameservers = []
        self.traceroute_methods = []

        if self.params is not None:
            # process parameters
            if "traceroute_methods" in self.params:
                self.traceroute_methods = self.params['traceroute_methods']
            if "exclude_nameservers" in self.params:
                self.exclude_nameservers = self.params['exclude_nameservers']
            if "tls_for_all" in self.params:
                self.tls_for_all = self.params['tls_for_all']

        if os.geteuid() != 0:
            logging.info("Centinel is not running as root, "
                         "traceroute will be limited to UDP.")
            # only change to udp if method list was not empty before
            if self.traceroute_methods:
                self.traceroute_methods = ["udp"]

    def run(self):
        for input_file in self.input_files.items():
            logging.info("Testing input file %s..." % (input_file[0]))
            # Initialize the results for this input file.
            # This can be anything from file name to version
            # to any useful information.
            result = {"file_name": input_file[0]}

            try:
                self.run_file(input_file, result)
            except KeyboardInterrupt:
                logging.warn("Experiment interrupted, storing partial results...")

            self.results.append(result)

    def run_file(self, input_file, result):
        file_name, file_contents = input_file

        run_start_time = time.time()

        tcp_connect_inputs = []
        http_inputs = []
        tls_inputs = []
        dns_inputs = []
        traceroute_inputs = []
        url_metadata_results = {}
        file_metadata = {}
        file_comments = []
        index_row = None

        # first parse the input and create data structures
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
            http_ssl = False
            ssl_port = 443
            port = 80

            # parse the URL to extract netlocation, HTTP path, domain name,
            # and HTTP method (SSL or plain)
            try:
                urlparse_object = urlparse.urlparse(url)
                http_netloc = urlparse_object.netloc

                # if netloc is not urlparse-able, add // to the start
                # of URL
                if http_netloc == '':
                    urlparse_object = urlparse.urlparse('//%s' % url)
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

                if len(http_netloc.split(':')) == 2:
                    port = int(http_netloc.split(':')[1])

            except Exception as exp:
                logging.exception("%s: failed to parse URL: %s" % (url, exp))
                http_netloc = url
                http_ssl = False
                port = 80
                ssl_port = 443
                http_path = '/'
                domain_name = url

            # TCP connect
            if http_ssl:
                if (domain_name, ssl_port) not in tcp_connect_inputs:
                    tcp_connect_inputs.append((domain_name, ssl_port))
            else:
                if (domain_name, port) not in tcp_connect_inputs:
                    tcp_connect_inputs.append((domain_name, port))


            # HTTP GET
            http_inputs.append({"host": http_netloc,
                                "path": http_path,
                                "ssl": http_ssl,
                                "url": url})

            # TLS certificate
            # this will only work if the URL starts with https://, or
            # if tls_for_all config parameter is set
            if self.tls_for_all or http_ssl:
                key = "%s:%s" % (domain_name, ssl_port)
                if key not in tls_inputs:
                    tls_inputs.append(key)

            # DNS Lookup
            if domain_name not in dns_inputs:
                dns_inputs.append(domain_name)

            # Traceroute
            if domain_name not in traceroute_inputs:
                traceroute_inputs.append(domain_name)

            # Meta-data
            url_metadata_results[url] = meta

        # the actual tests are run concurrently here

        if tcp_connect is not None:
            shuffle(tcp_connect_inputs)
            start = time.time()
            logging.info("Running TCP connect tests...")
            result["tcp_connect"] = {}
            tcp_connect.tcp_connect_batch(tcp_connect_inputs, results=result["tcp_connect"])
            elapsed = time.time() - start
            logging.info("Running TCP requests took "
                         "%d seconds for %d hosts and ports." % (elapsed,
                                                      len(tcp_connect_inputs)))

        shuffle(http_inputs)
        start = time.time()
        logging.info("Running HTTP GET requests...")
        result["http"] = {}

        try:
            http.get_requests_batch(http_inputs, results=result["http"])
        # backward-compatibility with verions that don't support this
        except TypeError:
            result["http"] = http.get_requests_batch(http_inputs)

        elapsed = time.time() - start
        logging.info("HTTP GET requests took "
                     "%d seconds for %d URLs." % (elapsed,
                                                  len(http_inputs)))
        shuffle(tls_inputs)
        start = time.time()
        logging.info("Running TLS certificate requests...")
        result["tls"] = {}

        try:
            tls.get_fingerprint_batch(tls_inputs, results=result["tls"])
        # backward-compatibility with verions that don't support this
        except TypeError:
            result["tls"] = tls.get_fingerprint_batch(tls_inputs)

        elapsed = time.time() - start
        logging.info("TLS certificate requests took "
                     "%d seconds for %d domains." % (elapsed,
                                                     len(tls_inputs)))
        shuffle(dns_inputs)
        start = time.time()
        logging.info("Running DNS requests...")
        result["dns"] = {}
        if len(self.exclude_nameservers) > 0:
            logging.info("Excluding nameservers: %s" % ", ".join(self.exclude_nameservers))

            try:
                dnslib.lookup_domains(dns_inputs, results=result["dns"],
                                      exclude_nameservers=self.exclude_nameservers)
            # backward-compatibility with verions that don't support this
            except TypeError:
                result["dns"] = dnslib.lookup_domains(dns_inputs,
                        exclude_nameservers=self.exclude_nameservers)
        else:
            try:
                dnslib.lookup_domains(dns_inputs, results=result["dns"])
            # backward-compatibility with verions that don't support this
            except TypeError:
                result["dns"] = dnslib.lookup_domains(dns_inputs)

        elapsed = time.time() - start
        logging.info("DNS requests took "
                     "%d seconds for %d domains." % (elapsed,
                                                     len(dns_inputs)))

        for method in self.traceroute_methods:
            shuffle(traceroute_inputs)
            start = time.time()
            logging.info("Running %s traceroutes..." % (method.upper()))
            result["traceroute.%s" % method] = {}

            try:
                traceroute.traceroute_batch(traceroute_inputs, results=result["traceroute.%s" % method], method=method)
            # backward-compatibility with verions that don't support this
            except TypeError:
                result["traceroute.%s" % method] = traceroute.traceroute_batch(traceroute_inputs, method)

            elapsed = time.time() - start
            logging.info("Traceroutes took %d seconds for %d "
                         "domains." % (elapsed, len(traceroute_inputs)))

        # if we have an index row, we should turn URL metadata
        # into dictionaries
        if index_row is not None:
            indexed_url_metadata = {}
            for url, meta in url_metadata_results.items():
                indexed_meta = {}
                try:
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

        run_finish_time = time.time()
        elapsed = run_finish_time - run_start_time
        result["total_time"] = elapsed
        logging.info("Testing took a total of %d seconds." % elapsed)
