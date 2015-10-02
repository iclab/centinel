from base64 import b64encode
import dns.rdatatype
import dns.message
import dns.resolver
import logging
import select
import socket
import threading
import time


def get_ips(host, nameserver=None, record="A"):
    nameservers = []
    if nameserver is not None:
        nameservers = [nameserver]
    return lookup_domain(host, nameservers=nameservers, rtype=record)


def lookup_domain(domain, nameservers=[], rtype="A", timeout=2):
    """Wrapper for DNSQuery method"""
    dns_exp = DNSQuery(domains=[domain], nameservers=nameservers, rtype=rtype,
                       timeout=timeout)
    return dns_exp.lookup_domain(domain)


def lookup_domains(domains, nameservers=[], rtype="A", timeout=10):
    dns_exp = DNSQuery(domains=domains, nameservers=nameservers, rtype=rtype,
                       timeout=timeout)
    return dns_exp.lookup_domains()


def send_chaos_queries():
    dns_exp = DNSQuery()
    return dns_exp.send_chaos_queries()


class DNSQuery():
    """Class to store state for all of the DNS queries"""

    def __init__(self, domains=[], nameservers=[], rtype="A", timeout=10,
                 max_threads=100):
        """Constructor for the DNS query class

        Params:
        nameserver- the nameserver to use, defaults to the local resolver
        rtype- the record type to lookup (as text), by default A
        timeout- how long to wait for a response, by default 10 seconds

        """
        self.domains = domains
        self.rtype = rtype
        self.timeout = timeout
        self.max_threads = max_threads
        if nameservers == []:
            nameservers = dns.resolver.Resolver().nameservers
        self.nameservers = nameservers
        self.results = {}
        self.threads = []

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
                if reads == []:
                    self.results[name][nameserver] = None
                else:
                    response = reads[0].recvfrom(4096)[0]
                    self.results[name][nameserver] = b64encode(response)
        return self.results

    def lookup_domains(self):
        """More complex DNS primitive that lookups domains concurrently

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
                thread.start()
                self.threads.append(thread)
            if thread_error:
                break
            ind += 1

        for thread in self.threads:
            thread.join(self.timeout * 3)
        return self.results

    def lookup_domain(self, domain, nameserver=None, log_prefix = ''):
        """Most basic DNS primitive that lookups a domain, waits for a
        second response, then returns all of the results

        Params:
        domain- the domain to lookup
        nameserver- the nameserver to use

        Note: if you want to lookup multiple domains you *should not* use
        this function, you should use lookup_domains because this does
        blocking IO to wait for the second response

        """
        # get the resolver to use
        if nameserver is None:
            nameserver = self.nameservers[0]
        results = {'domain': domain, 'nameserver': nameserver}
        # construct the socket to use
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(self.timeout)

        logging.debug("%sQuerying DNS enteries for "
                      "%s (nameserver: %s)." % (log_prefix, domain, nameserver))

        # construct and send the request
        request = dns.message.make_query(domain,
                                         dns.rdatatype.from_text(self.rtype))
        results['request'] = b64encode(request.to_wire())
        sock.sendto(request.to_wire(), (nameserver, 53))

        # read the first response from the socket
        reads, _, _ = select.select([sock], [], [], self.timeout)
        # if we didn't get anything, then set the results to nothing
        if reads == []:
            results['response1'] = None
            self.results[domain] = results
            return results
        response = reads[0].recvfrom(4096)[0]
        results['response1'] = b64encode(response)
        resp = dns.message.from_wire(response)
        results['response1-ips'] = self.parse_out_ips(resp)

        # if we have made it this far, then wait for the next response
        reads, _, _ = select.select([sock], [], [], self.timeout)
        # if we didn't get anything, then set the results to nothing
        if reads == []:
            results['response2'] = None
            self.results[domain] = results
            return results
        response = reads[0].recvfrom(4096)[0]
        results['response2'] = b64encode(response)
        resp = dns.message.from_wire(response)
        results['response2-ips'] = self.parse_out_ips(resp)
        self.results[domain] = results
        return results

    def parse_out_ips(self, message):
        """Given a message, parse out the ips in the answer"""

        ips = []
        for entry in message.answer:
            for rdata in entry.items:
                ips.append(rdata.to_text())
        return ips
