import dns.resolver

def get_ips(host, nameserver=None, record="A"):
    resolver = dns.resolver.Resolver()

    if nameserver:
        resolver.nameservers = [nameserver]

    #XXX: ipv6?
    answers = resolver.query(host, record)

    ips = [rdata.address for rdata in answers]

    return ips
