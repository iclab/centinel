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
from random import shuffle
import time
import urlparse

from centinel.experiment import Experiment
from centinel.primitives import dnslib
from centinel.primitives import tls
import centinel.primitives.http as http
import centinel.primitives.traceroute as traceroute


class BaselineExperiment(Experiment):
    name = "baseline"
    # country-specific, world baseline
    # this can be overridden by the main thread
    input_files = ['country.csv', 'world.csv']

    def __init__(self, input_files):
        self.input_files = input_files
        self.results = []

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
        for input_file in self.input_files.items():
            logging.info("Testing input file %s..." % (input_file[0]))
            self.results.append(self.run_file(input_file))

    def run_file(self, input_file):
        file_name, file_contents = input_file

        # Initialize the results for this input file.
        # This can be anything from file name to version
        # to any useful information.
        result = {"file_name": file_name}
        run_start_time = time.time()

        http_results = {}
        http_inputs  = []
        tls_results = {}
        tls_inputs  = []
        dns_results = {}
        dns_inputs  = []
        traceroute_results = {}
        traceroute_inputs  = []
        url_metadata_results = {}
        file_metadata = {}
        file_comments = []
        index_row = None
        comments = ""

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
                logging.exception("%s: failed to parse URL: %s" % (url, exp))
                http_netloc = url
                http_ssl    = False
                ssl_port = 443
                http_path   = '/'
                domain_name = url

            # HTTP GET
            http_inputs.append( { "host": http_netloc,
                                  "path": http_path,
                                  "ssl":  http_ssl,
                                  "url":  url
                                } )

            # TLS certificate
            # this will only work if the URL starts with https://
            if http_ssl:
                tls_inputs.append("%s:%s" % (domain_name, ssl_port))

            # DNS Lookup
            dns_inputs.append(domain_name)

            # Traceroute
            traceroute_inputs.append(domain_name)

            # Meta-data
            url_metadata_results[url] = meta

        # the actual tests are run concurrently here

        shuffle(http_inputs)
        start = time.time()
        logging.info("Running HTTP GET requests...")
        result["http"] = http.get_requests_batch(http_inputs)
        elapsed = time.time() - start
        logging.info("HTTP GET requests took "
                     "%d seconds for %d URLs." % (elapsed,
                                                  len(http_inputs)))
        shuffle(tls_inputs)
        start = time.time()
        logging.info("Running TLS certificate requests...")
        result["tls"] = tls.get_fingerprint_batch(tls_inputs)
        elapsed = time.time() - start
        logging.info("TLS certificate requests took "
                     "%d seconds for %d domains." % (elapsed,
                                                     len(tls_inputs)))
        shuffle(dns_inputs)
        start = time.time()
        logging.info("Running DNS requests...")
        result["dns"] = dnslib.lookup_domains(dns_inputs)
        elapsed = time.time() - start
        logging.info("DNS requests took "
                     "%d seconds for %d domains." % (elapsed,
                                                     len(dns_inputs)))

        for method in self.traceroute_methods:
            shuffle(traceroute_inputs)
            start = time.time()
            logging.info("Running %s traceroutes..." % (method.upper()) )
            result["traceroute.%s" % (method) ] = (
                traceroute.traceroute_batch(traceroute_inputs, method))
            elapsed = time.time() - start
            logging.info("Traceroutes took %d seconds for %d "
                         "domains." % (elapsed, len(traceroute_inputs)))

        # if we have an index row, we should turn URL metadata
        # into dictionaries
        if index_row is not None:
            indexed_url_metadata = {}
            for url, meta in url_metadata_results.items():
                try:
                    indexed_meta = {}
                    for i in range(1,len(index_row)):
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
        logging.info("Testing took a total of %d seconds." % (elapsed) )
        return result
