from base64 import b64encode
import dns.rdatatype
import dns.message
import dns.resolver
import logging
import select
import socket
import threading
import time

MAX_THREAD_START_RETRY = 10
THREAD_START_DELAY = 3

def get_ips(host, nameserver=None, record="A"):
    nameservers = []
    if nameserver is not None:
        nameservers = [nameserver]
    return lookup_domain(host, nameservers=nameservers, rtype=record)


def lookup_domain(domain, nameservers=[], rtype="A",
                  exclude_nameservers=[], timeout=2):
    """Wrapper for DNSQuery method"""
    dns_exp = DNSQuery(domains=[domain], nameservers=nameservers, rtype=rtype,
                       exclude_nameservers=exclude_nameservers, timeout=timeout)
    return dns_exp.lookup_domain(domain)


def lookup_domains(domains, results={}, nameservers=[], exclude_nameservers=[],
                   rtype="A", timeout=2):
    dns_exp = DNSQuery(domains=domains, results=results, nameservers=nameservers, 
                       rtype=rtype, exclude_nameservers=exclude_nameservers, 
                       timeout=timeout)
    return dns_exp.lookup_domains()


def send_chaos_queries():
    dns_exp = DNSQuery()
    return dns_exp.send_chaos_queries()


class DNSQuery:
    """Class to store state for all of the DNS queries"""

    def __init__(self, domains=[], results={}, nameservers=[], exclude_nameservers=[],
                 rtype="A", timeout=10, max_threads=100):
        """Constructor for the DNS query class

        Params:
        nameserver- the nameserver to use, defaults to the local resolver
        rtype- the record type to lookup (as text), by default A
        timeout- how long to wait for a response, by default 10 seconds

        """
        self.domains = domains
        self.results = results
        self.rtype = rtype
        self.timeout = timeout
        self.max_threads = max_threads
        if len(nameservers) == 0:
            nameservers = dns.resolver.Resolver().nameservers
        # remove excluded nameservers
        if len(exclude_nameservers) > 0:
            for nameserver in exclude_nameservers:
                if nameserver in nameservers:
                    nameservers.remove(nameserver)
        # include google nameserver
        if "8.8.8.8" not in nameservers:
            nameservers.append("8.8.8.8")
        self.nameservers = nameservers
        self.threads = []
        # start point of port number to be used
        self.port = 30000
        # create thread lock for port number index
        self.port_lock = threading.Lock()

    def send_chaos_queries(self):
        """Send chaos queries to identify the DNS server and its manufacturer

        Note: we send 2 queries for BIND stuff per RFC 4892 and 1
        query per RFC 6304

        Note: we are not waiting on a second response because we
        shouldn't be getting injected packets here

        """
        names = ["HOSTNAME.BIND", "VERSION.BIND", "ID.SERVER"]
        self.results = {'exp-name': "chaos-queries"}
        for name in names:
            self.results[name] = {}
            for nameserver in self.nameservers:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(self.timeout)
                query = dns.message.make_query(name,
                                               dns.rdatatype.from_text("TXT"),
                                               dns.rdataclass.from_text("CH"))
                sock.sendto(query.to_wire(), (nameserver, 53))
                reads, _, _ = select.select([sock], [], [], self.timeout)
                if len(reads) == 0:
                    self.results[name][nameserver] = None
                else:
                    response = reads[0].recvfrom(4096)[0]
                    self.results[name][nameserver] = b64encode(response)
        return self.results

    def lookup_domains(self):
        """More complex DNS primitive that looks up domains concurrently

        Note: if you want to lookup multiple domains, you should use
        this function
        """
        thread_error = False
        thread_wait_timeout = 200
        ind = 1
        total_item_count = len(self.domains)
        for domain in self.domains:
            for nameserver in self.nameservers:
                wait_time = 0
                while threading.active_count() > self.max_threads:
                    time.sleep(1)
                    wait_time += 1
                    if wait_time > thread_wait_timeout:
                        thread_error = True
                        break

                if thread_error:
                    self.results["error"] = "Threads took too long to finish."
                    break
                log_prefix = "%d/%d: " % (ind, total_item_count)
                thread = threading.Thread(target=self.lookup_domain,
                                          args=(domain, nameserver,
                                                log_prefix))
                thread.setDaemon(1)

                thread_open_success = False
                retries = 0
                while not thread_open_success and retries < MAX_THREAD_START_RETRY:
                    try:
                        thread.start()
                        self.threads.append(thread)
                        thread_open_success = True
                    except:
                        retries += 1
                        time.sleep(THREAD_START_DELAY)
                        logging.error("%sThread start failed for %s, retrying... (%d/%d)" % (log_prefix, domain, retries, MAX_THREAD_START_RETRY))

                if retries == MAX_THREAD_START_RETRY:
                    logging.error("%sCan't start a new thread for %s after %d retries." % (log_prefix, domain, retries))

            if thread_error:
                break
            ind += 1

        for thread in self.threads:
            thread.join(self.timeout * 3)
        return self.results

    def lookup_domain(self, domain, nameserver=None, log_prefix=''):
        """Most basic DNS primitive that looks up a domain, waits for a
        second response, then returns all of the results

        :param domain: the domain to lookup
        :param nameserver: the nameserver to use
        :param log_prefix:
        :return:

        Note: if you want to lookup multiple domains you *should not* use
        this function, you should use lookup_domains because this does
        blocking IO to wait for the second response

        """
        if domain not in self.results:
            self.results[domain] = []
        # get the resolver to use
        if nameserver is None:
            logging.debug("Nameserver not specified, using %s" % self.nameservers[0])
            nameserver = self.nameservers[0]
        results = {'domain': domain, 'nameserver': nameserver}
        # construct the socket to use
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        # set port number and increment index:
        interrupt = False
        with self.port_lock:
            counter = 1
            while True:
                if counter > 100:
                    logging.warning("Stop trying to get an available port")
                    interrupt = True
                    break
                try:
                    sock.bind(('', self.port))
                    break
                except socket.error:
                    logging.debug("Port {} already in use, try next one".format(self.port))
                    self.port += 1
                    counter += 1
            self.port += 1

        if interrupt:
            sock.close()
            results['error'] = 'Failed to run DNS test'
            self.results[domain].append(results)
            return results

        logging.debug("%sQuerying DNS enteries for "
                      "%s (nameserver: %s)." % (log_prefix, domain, nameserver))

        # construct and send the request
        request = dns.message.make_query(domain,
                                         dns.rdatatype.from_text(self.rtype))
        results['request'] = b64encode(request.to_wire())
        sock.sendto(request.to_wire(), (nameserver, 53))

        # read the first response from the socket
        try:
            response = sock.recvfrom(4096)[0]
            results['response1'] = b64encode(response)
            resp = dns.message.from_wire(response)
            results['response1-ips'] = parse_out_ips(resp)

            # first domain name in response should be the same with query
            # domain name
            for entry in resp.answer:
                if domain.lower() != entry.name.to_text().lower()[:-1]:
                    logging.debug("%sWrong domain name %s for %s!"
                                  % (log_prefix, entry.name.to_text().lower()[:-1], domain))
                    results['response1-domain'] = entry.name.to_text().lower()[:-1]
                break
        except socket.timeout:
            # if we didn't get anything, then set the results to nothing
            logging.debug("%sQuerying DNS enteries for "
                          "%s (nameserver: %s) timed out!" % (log_prefix, domain, nameserver))
            sock.close()
            results['response1'] = None
            self.results[domain].append(results)
            return results

        # if we have made it this far, then wait for the next response
        try:
            response2 = sock.recvfrom(4096)[0]
            results['response2'] = b64encode(response2)
            resp2 = dns.message.from_wire(response2)
            results['response2-ips'] = parse_out_ips(resp2)

            # first domain name in response should be the same with query
            # domain name
            for entry in resp2.answer:
                if domain.lower != entry.name.to_text().lower()[:-1]:
                    logging.debug("%sWrong domain name %s for %s!"
                                  % (log_prefix, entry.name.to_text().lower()[:-1], domain))
                    results['response2-domain'] = entry.name.to_text().lower()[:-1]
                break
        except socket.timeout:
            # no second response
            results['response2'] = None

        sock.close()
        self.results[domain].append(results)
        return results


def parse_out_ips(message):
    """Given a message, parse out the ips in the answer"""

    ips = []
    for entry in message.answer:
        for rdata in entry.items:
            ips.append(rdata.to_text())
    return ips
