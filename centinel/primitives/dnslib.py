from base64 import b64encode
import dns.rdatatype
import dns.message
import dns.resolver
import select
import socket


def get_ips(host, nameserver=None, record="A"):
    nameservers = []
    if nameserver is not None:
        nameservers = [nameserver]
    return lookup_domain(domain, nameservers=nameservers, record=record)


def lookup_domain(domain, nameservers=[], rtype="A", timeout=10):
    """Wrapper for DNSQuery method"""
    dns_exp = DNSQuery([domain], nameservers)
    return dns_exp.lookup_domain(domain, nameservers=nameservers, rtype=rtype,
                                 timeout=timeout)


def send_chaos_query(record="", nameserver=None, ):
    

class DNSQuery():
    """Class to store state for all of the DNS queries"""

    def __init__(self, domains, nameservers=[], rtype="A", timeout=10):
        pass

    def lookup_domain(self, domain, nameserver=None, rtype="A", timeout=10):
        """Most basic DNS primitive that lookups a domain, waits for a
        second response, then returns all of the results

        Params:
        domain- the domain to lookup
        nameserver- the nameserver to use, defaults to the local resolver
        rtype- the record type to lookup (as text), by default A
        timeout- how long to wait for a response, by default 10 seconds

        Note: if you want to lookup multiple domains you *should not* use
        this function, you should use lookup_domains because this does
        blocking IO to wait for the second response

        """
        # get the resolver to use
        if nameserver is None:
            nameserver = dns.resolver.Resolver().nameservers[0]
        results = {'domain': domain, 'nameserver': nameserver}
        # construct the socket to use
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        # construct and send the request
        request = dns.message.make_query(domain, dns.rdatatype.from_text(rtype))
        result['request'] = b64encode(request.to_wire())
        sock.sendto(request.to_wire(), (nameserver, 53))

        # read the first response from the socket
        reads, _, _ = select.select([sock], [], [], timeout)
        # if we didn't get anything, then set the results to nothing
        if reads == []:
            results['response1'] = None
            return results
        response = reads[0].recvfrom(4096)[0]
        results['response1'] = b64encode(response)
        results['response1-ips'] = self.parse_out_ips(dns.message.from_wire(response))

        # if we have made it this far, then wait for the next response
        reads, _, _ = select.select([sock], [], [], timeout)
        # if we didn't get anything, then set the results to nothing
        if reads == []:
            results['response2'] = None
            return results
        response = reads[0].recvfrom(4096)[0]
        results['response2'] = b64encode(response)
        results['response2-ips'] = self.parse_out_ips(dns.message.from_wire(response))
        return results

    def parse_out_ips(self, message):
        """Given a message, parse out the ips in the answer"""

        ips = []
        for entry in message.answer:
            for rdata in entry.items:
                ips.append(rdata.to_text())
        return ips
