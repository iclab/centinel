"""
Contains all the functions
the client provides for network measurements.
"""


import requests
import logging
from itertools import chain
import dns.resolver
import dns.entropy
import dns.rdatatype
import urlparse
from requests.utils import requote_uri, get_unicode_from_response
import sys

sys.path.append("ponylib")
import scapy.all as sc
import pcapwriter  # this is our own version of scapy's pcapw
from snifferthread import SnifferThread

log = logging.getLogger("pony")


def getreversedns(hostname, resolver="", timeout=2):
    ans = sc.sr1(sc.IP(dst=resolver) / sc.UDP() / sc.DNS(rd=1,
                 qd=sc.DNSQR(qname=hostname,
                 qtype='PTR')), timeout=timeout)
    result = ans.getlayer("DNS").an
    result = ""
    return result


def addresult(output, result, name, value):
    if not output or name in output:
        result[name] = value
    return


class PonyFunctions:
    """The PonyFunctions class provides a number of static functions that
    directly map onto the instructions in the experiment specification.
    The following functions are not directly called by the specification,
    but rather called by the :mod:`Task <task>` thread which is given the
    instruction and the ..."""

    @staticmethod
    def pony_ping(output, ip, port=80, packettype="icmp", mincount=1,
                  interval=0, retry=1, timeout=2, snifftimeout=0):
        """Performs a ping to the address.

        :param output: comma-separated string of requested output fields.
          If an empty string is given, output is set to
          ``"response,rtt,pcap"``.
          Can contain one or more of the following:

          * ``response``: :token:`1` if any responses were received,
            :token:`0` otherwise.
          * ``rtt``: average round-trip time.
          * ``pcap``: if specified, the ``pcap`` field will contain a
            ``.pcap``-formatted packet capture of all incoming traffic,
            encoded as a base64 string.
        :param ip: the IP address of the host to ping. If a domain name is
          specified instead, Scapy will try to resolve it into an IP. To be
          safe, it is recommended to use the dedicated DNS function to
          resolve host names.
        :param port: the destination port on which to contact the host. This
          parameter does not affect ICMP packets. The default is :token:`80`,
          which is likely to work with TCP packets.
          Note that UDP pings, on the other
          hand, are expected to trigger an ICMP "port unreachable" response,
          which requires that the packet be sent to a likely-closed port
          such as :token:`0`.
        :param packettype: can be one of the following, with ``"icmp"``
          being the default value:

          * ``icmp``: an ICMP type 8 packet (echo request) is sent to the
            host.
          * ``tcpsyn``: a TCP packet with ``SYN`` flag set is sent to the
            host, pretending to initiate a new TCP session and expecting
            back a TCP ``SYN, ACK`` packet.
          * ``tcpack``: a TCP packet with ``ACK`` flag set is sent to the
            host, which typically acknowledges a previous transmission
            or handshake. Since none has taken place, a ``RST`` packet is
            expected from the server.
          * ``udp``: since many applications don't respond to random incoming
            UDP packets on their port, we are most likely to trigger a
            response by pinging a port that is likely closed, such as
            port :token:`0` or :token:`31338`. Note that the default port
            for this function is set to :token:`80`. Also note that closed
            ports are likely blocked if the host is behind a NAT/firewall.

        :param mincount: the number of response packets to capture. If
          ``mincount`` > :token:`1`, then ``mincount`` packets are sent out
          and captured.
        :param interval: if ``mincount`` > :token:`1`, this specifies the
          interval, in seconds, between sending out two packets.
        :param retry: the number of times Scapy will try to resend unanswered
          packets.
        :param timeout: the time, in seconds, to wait for a response packet.
        :param snifftimeout: the minimum time, in seconds, to run the packet
          capture.
        """

        result = dict()

        sport = int(sc.RandNum(1024, 65535))
        packet = sc.IP(dst=ip)
        if packettype == "icmp":
            packet /= sc.ICMP()
        elif packettype == "tcpsyn":
            # try a TCP SYN packet on port 80 (expect SYNACK back)
            port = 80 if not port else port
            packet /= sc.TCP(sport=sport, dport=port, flags="S")
        elif packettype == "tcpack":
            # try a TCP ACK packet on port 80 (expect RST back)
            port = 80 if not port else port
            packet /= sc.TCP(sport=sport, dport=port, flags="A")
        elif packettype == "udp":
            # try a UDP packet to a likely-closed port (expect ICMP
            # unreachable back if the host is live)
            packet /= sc.UDP(sport=sport, dport=port)

        if not output or "pcap" in output:
            # build lfilter
            if packettype == "icmp":
                lfilter = lambda p: p.haslayer(sc.IP) and p.proto == 1
            elif packettype == "tcpsyn" or packettype == "tcpack":
                lfilter = lambda p: (p.haslayer(sc.IP)
                                     and ((p.proto == 6 and
                                          p.sport in [port, sport] and
                                          p.dport in [port, sport]) or
                                          p.proto == 1))
            elif packettype == "udp":
                lfilter = lambda p: (p.haslayer(sc.IP)
                                     and ((p.proto == 17 and
                                          p.sport in [port, sport] and
                                          p.dport in [port, sport]) or
                                          p.proto == 1))

            sniffer = SnifferThread(l2socket=sc.conf.L2socket,
                                    lfilter=lfilter,
                                    timeout=snifftimeout, count=mincount)
            sniffer.setDaemon(True)
            sniffer.start()

        # send packet, get result
        if mincount == 1:
            ans, unans = sc.sr(packet, inter=interval, retry=retry,
                               timeout=timeout, verbose=0)
        elif mincount > 1:
            ans, unans = sc.srloop(packet, inter=interval, retry=retry,
                                   count=mincount, timeout=timeout, verbose=0)

        # get sniff result
        if not output or "pcap" in output:
            sniffer.stop()
            sniffer.join()
            pcap = sniffer.getPacketList()
            pcapw = pcapwriter.PcapWriter(sc.conf.l2types)
            if pcap:
                pcapw.write(pcap)
                result["pcap"] = pcapw.getBase64String()

        # make sure the response didnt consist of BS redirect packets.
        # the response must come from the right IP.
        ans[:] = [a for a in ans if a[0].dst == a[1].src]
        if ans:  # if we got any answer packets at all
            addresult(output, result, "response", 1)
            rtt = reduce(lambda x, y: x + y,
                         [(ansPkt.time - sentPkt.sent_time)
                          for (sentPkt, ansPkt) in ans])
            rtt = 1000 * rtt / len(ans)
            addresult(output, result, "rtt", rtt)
            addresult(output, result, "ans", ans)
        elif not ans:
            addresult(output, result, "response", 0)

        log.info("Pinged IP " + ip + ". " + str(len(ans)) +
                 " response(s) received.")
        return result

    @staticmethod
    def pony_traceroute(output, ip, packettype="icmp", retry=3, maxttl=30,
                        port=80, incrementport=0, timeout=5,
                        snifftimeout=0, reverseresolver="8.8.8.8"):
        """A vanilla traceroute implementation. Sends packets out, TTLs
        increasing, and waits for them to come back.

        :param output: comma-separated string of requested output fields. If
          an empty string is given, output is set to ``"hopsips,hopsnames,
          redirected,success,pcap"``. Can contain one or more of the
          following:

          * ``hopsips``: a comma-separated string listing the IPs of all
            hops which responded. Hops which did not respond will be
            listed as an empty string (e.g. ``192.168.2.1,,69.59.261.32``).
            Note that certain responses, such as redirect messages, will
            appear as valid IPs. The IPs are sorted by ascending hop number.
          * ``hopsnames``: a comma-separated string listing the names of
            the hosts which responded.
          * ``pcap``: if specified, the ``pcap`` field will contain a
            ``.pcap``-formatted packet capture of all incoming traffic,
            encoded as a base64 string.

        :param ip: the IP address of the host to perform a traceroute to.
          If a domain name is specified instead, Scapy will try to resolve
          it into an IP. To be safe, it is recommended to use the dedicated
          DNS function to resolve host names.

        :param packettype: can be one of the following, with ``"icmp"`` being
          the default:

          * ``icmp``: an ICMP type 8 packet (echo request) is sent to the
            host.
          * ``icmp30``: an ICMP type 30 packet (traceroute request) is sent
            to the host. Note that this function is provided for completness'
            sake; while type 30 packets are standardized in :rfc:`1393`,
            many routers ignore them.
          * ``tcpsyn``: a TCP packet with ``SYN`` flag set is sent to the
            host, pretending to initiate a new TCP session and expecting back
            a TCP ``SYN, ACK`` packet.
          * ``tcpack``: a TCP packet with ``ACK`` flag set is sent to the
            host, which typically acknowledges a previous transmission or
            handshake. Since none has taken place, a ``RST`` packet is
            expected from the server.
          * ``udp``: sends a UDP packet to the host.
          * ``raw``: sends a simple IP packet without any transport-layer
            content (such as TCP or UDP).
        :param retry: the number of times Scapy will try to resend unanswered
          packets.
        :param maxttl: the maximum number of hops to try before giving up.
        :param port: the destination port on which to contact the hosts.
        :param incrementport: if set to :token:`1`, the destination port
          number is incremented by 1 with every hop. This is usually done
          with UDP packets to make it easier to identify out-of-order
          responses, but typically not with ICMP or TCP.
          The default is :token:`0`.
        :param timeout: the time, in seconds, to wait for a response packet.
        :param snifftimeout: the minimum time, in seconds, to run the packet
          capture.
        :param reverseresolver: the DNS resolver to use for reverse DNS
          lookups, if ``hopsnames`` is specified in ``output``.

        """
        result = dict()

        # first build the packet we're trying to send
        packet = sc.IP(dst=ip)
        if not packettype or packettype == "icmp":
            packet /= sc.ICMP(type=8)
        elif packettype == "icmp30":
            packet /= sc.ICMP(type=30)
        elif packettype == "udp":
            packet /= sc.UDP(dport=port)
        elif packettype == "tcpsyn":
            packet /= sc.TCP(dport=port, flags="S")
        elif packettype == "tcpack":
            packet /= sc.TCP(dport=port, flags="A")
        elif packettype == "raw":
            # just use the IP packet as is
            pass

        # this is for interim storage
        hopsips = []
        hopsnames = []
        pcap = []

        getreverse = not output or "hopsnames" in output
        destinationreached = False
        redirectencountered = False

        # start the sniffer if we need it!
        if not output or "pcap" in output:
            # build lfilter
            lfilter = lambda p: p.haslayer(sc.IP) and p.proto == 1
            sniffer = SnifferThread(l2socket=sc.conf.L2socket,
                                    lfilter=lfilter,
                                    timeout=snifftimeout, count=maxttl)
            sniffer.setDaemon(True)
            sniffer.start()

        sc.conf.verb = 0
        # now send those packets out!
        for ttl in range(0, maxttl + 1):  # TODO WARNING SET BACK TO 1
            if destinationreached:
                addresult(output, result, "hopscount", ttl - 1)
                break
            packet.ttl = ttl
            ans, unans = sc.sr(packet, retry=retry, timeout=timeout, verbose=0)
            # store everything in pcap for now
            pcap.append(list(chain.from_iterable(ans + unans)))
            # first, see if we got anything back at all.
            if not ans:
                log.debug("Packet unanswered.")
                if len(unans) == retry:
                    log.debug("Hop " + ttl + " unanswered after " + retry +
                              " times. Continuing.")
                    hopsips.append("")
                    hopsnames.append("")
                    continue
            # if we got something back, take it (the first one) and see what it
            # is
            for (sntpkt, rspnspkt) in ans:
                # first make sure we got an ICMP back
                if rspnspkt.proto == 1:
                    if (rspnspkt.type == 0 or
                            (rspnspkt.type == 3 and rspnspkt.code == 3)):
                        # looks like the destination replying! yay
                        log.debug("Destination reached.")
                        destinationreached = True
                        hopsips.append(rspnspkt.src)
                        if getreverse:
                            hopsnames.append(getreversedns(
                                rspnspkt.src, reverseresolver))
                        break
                    elif rspnspkt.type == 11:
                        # time exceeded. we're on the way
                        log.debug("Time exceeded")
                        hopsips.append(rspnspkt.src)
                        if getreversedns:
                            hopsnames.append(getreversedns(
                                rspnspkt.src, reverseresolver))
                        break
                    elif rspnspkt.type == 5:
                        # we got a redirect. hhmmm. sucks.
                        # we'll keep trying and see what happens.
                        log.debug("Redirected.")
                        hopsips.append(rspnspkt.src)
                        if getreversedns:
                            hopsnames.append(getreversedns(
                                rspnspkt.src, reverseresolver))
                        # and make note of it
                        redirectencountered = True
                    else:
                        log.debug("Another response packet:" +
                                  rspnspkt.summary())
                elif rspnspkt.proto == 6:  # TCP
                    if rspnspkt.src == sntpkt.dst:
                        # looks like the destination replying! yay
                        log.debug("Destination reached.")
                        destinationreached = True
                        hopsips.append(rspnspkt.src)
                        if getreversedns:
                            hopsnames.append(getreversedns(
                                rspnspkt.src, reverseresolver))
                        break
                    else:
                        log.debug("Unexpected TCP repsonse: ")
                else:
                    log.debug("Another type of response:" + rspnspkt.summary())
            if incrementport == 1:
                port += 1

        # get sniff result
        if not output or "pcap" in output:
            sniffer.stop()
            sniffer.join()
            pcap = sniffer.getPacketList()
            pcapw = pcapwriter.PcapWriter(sc.conf.l2types)
            if pcap:
                pcapw.write(pcap)
                result["pcap"] = pcapw.getBase64String()

        addresult(output, result, "redirected", redirectencountered)
        addresult(output, result, "success", destinationreached)
        addresult(output, result, "hopsnames", ",".join(hopsnames))
        addresult(output, result, "hopsips", ",".join(hopsips))
        log.info("Ran traceroute to IP " + ip + ", host "
                 + ("" if destinationreached else "not ") + "reached.")
        return result

    @staticmethod
    def pony_fasttraceroute(output, ip, port=80, retry=1, maxttl=30,
                            truncate=1, timeout=5, reverseresolver=""):
        """
        Performs a traceroute using Scapy's built-in ``traceroute``
        function.

        This function is called "fast traceroute" since it sends all
        packets out simultaneously instead of waiting for a hop to respond
        before pinging the next hop. As a result, the traceroute results
        come in much faster---but at the price of not known a priori
        whether the traceroute will reach the destination or not.
        """
        result = dict()
        hopsips = [''] * maxttl
        hopsnames = [''] * maxttl
        hopscount = maxttl + 1
        ans, unans = sc.traceroute(ip, dport=port, retry=retry,
                                   timeout=timeout, maxttl=maxttl)
        getreverse = not output or "hopsnames" in output

        # now go through the responses and see what came back
        pcap = list(chain.from_iterable(ans + unans))
        if not ans:
            addresult(output, result, "fail", 1)

        for sntpkt, rspnspkt in ans:
            hopsips[sntpkt.ttl - 1] = rspnspkt.src
            if getreverse:
                hopsnames[sntpkt.ttl - 1] = getreversedns(rspnspkt.src,
                                                          reverseresolver)
            # now find out if this is the destination
            if (rspnspkt.proto == 1 and (rspnspkt.type == 0 or
                (rspnspkt.type == 3 and rspnspkt.code == 3)) or
                    (rspnspkt.type == 6 and rspnspkt.flags == "SA")):
                if (sntpkt.ttl - 1) < hopscount:
                    hopscount = sntpkt.ttl - 1

        # now truncate
        if truncate == 1:
            del hopsips[hopscount + 1:]
            del hopsnames[hopscount + 1:]

        if not output or "pcap" in output:
            pcapw = pcapwriter.PcapWriter(sc.conf.l2types)
            pcapw.write(pcap)
            result["pcap"] = pcapw.getBase64String()

        if hopscount <= maxttl:
            addresult(output, result, "success", 1)
        else:
            addresult(output, result, "success", 0)

        addresult(output, result, "hopscount", hopscount)
        addresult(output, result, "hopsips", ",".join(hopsips))
        addresult(output, result, "hopsnames", ",".join(hopsips))
        # still missing: byte count (ans[4][1].len)
        return result

    @staticmethod
    def paristraceroute():
        pass

    @staticmethod
    def pony_dns(output, domain, resolver="8.8.8.8", tcp=0,
                 port=53, mincount=0, wait_for_second=0, timeout=5,
                 snifftimeout=0, dnssec=0, fallback=0, recursive=1):
        """
        Performs a DNS query using the `dnspython <http://www.dnspython.org>`_
        library.

        :param output: comma-separated string of requested output fields. If
           an empty string is given, output is set to ``"A"`` per default.

           Can contain one or more of the following:

           * ``A``: Standard query for the IPv4 associated with the domain.
              Default.
           * ``AAAA``: Query for the IPv6 associated with the domain. Empty if
              none.
           * ``MX``: Query for the mailservers associated with the domain.
              Note that this generates four output fields:
           * ``TXT``: Query for the TXT record associated with the domain.
           * ``NS``: Query for the nameserver records associated with the
              domain.
           * ``SOA``: Query for the zone authority details associated with
              the domain.
           * ``CNAME``: Query for DNS aliases.
           * other stuff ... other dns types.
           * ``validated``: Will be :token:`1` if ``dnssec`` = :token:`1` and
              the DNS lookup could be validated via DNSSEC, and :token:`0`
              otherwise.
           * ``replies``: The number of response packets received. If no
              response was received within the ``timeout`` at all, this will
              be :token:`0`. If one or two packets were received
              (``wait_for_second`` = :token:`1` is required for the latter),
              this will be :token:`1` or :token:`2`, respectively.
           * ``pcap``: if specified, the ``pcap`` field
              will contain a ``.pcap``-formatted packet
              capture of all incoming traffic, encoded as a base64 string.
        :param domain: the fully-qualified domain name to look up, e.g.
           ``www.google.com`` or ``gmail.com``. Note that this can differ
           based on the query type, e.g. an ``MX`` query on ``www.google.com``
           will fail while one on ``google.com`` will succeed.
        :param resolver: the resolver to use, e.g. ``"8.8.8.8"`` for
           Google's public resolver. If left empty, the client's system's
           stub resolver will be used.
           :param tcp: if set to :token:`1`,
           the query will be sent in a TCP packet. The
           default is 0 and corresponds to UDP, which is the default for DNS
           queries. TCP is not supported by all DNS servers and typically
           only used for queries and/or responses that exceed UDP's maximum
           packet size of 1024 bytes. Note that DNS injection attacks (e.g.
           by the Great Firewall of China) are only known to work on UDP
           queries.
        :param port: the destination port on which to contact the DNS server.
           The default port for DNS queries (per :rfc:`1035`) is :token:`53`.
        :param mincount: the minimum number of packets to capture, if
           ``output`` contains ``pcap``.
        :param wait_for_second: if :token:`1`, the function will wait for
           two response packets to the same query. This can happen when
           DNS injection infrastructure is set up in the censorship
           environment. Both packets have to arrive within the time
           specified by the ``timeout`` parameter. It is advisable to
           request the ``replies`` field if this parameter is set to
           :token:`1` to find out how many packets were received.

           Note that, if two packets were indeed returned, there will
           be two fields for each of the relevant output fields listed
           above, with a ":token:`_2`" appended to the second packet's field
           name. Examples: ``A`` and ``A_2``, ``MXcount`` and ``MXcount_2``.
        :param timeout: the time, in seconds, to wait for DNS response
           packets. This time must allow for the arrival of a second packet,
           if ``wait_for_second`` is set and a second packet is expected.
        :param snifftimeout: the minimum time, in seconds, to run the
           packet capture, if ``output`` contains ``pcap``.
        :param dnssec: if set to :token:`1`, a DNSSEC validation of the
           results will be attempted. The ``validated`` field, if requested,
           will contain information on the outcome of this attempt.
        :param recursive: if set to :token:`1` (default), the
           ``recursion-desired`` bit will be set in the query (:rfc:`1035`).
        """
        result = dict()

        # {k: str(v).upper() for k, v in output}
        # perform a DNS query for each one of the following

        if not output:
            output = ["A"]

        dresolver = dns.resolver.Resolver()
        dresolver.lifetime = timeout
        dresolver.nameservers = [resolver]
        dresolver.port = port

        dnstypes = ["A", "AAAA", "MX", "CNAME", "DNAME", "NS", "SOA", "TXT"]

        # split output into DNS types and other output
        outputdnstypes = [a.upper() for a in output.split(",")
                          if a in dnstypes]
        output = [a for a in output.split(",") if a not in dnstypes]
        # if more than one outputdnstype is specified, produce warning
        if len(outputdnstypes) > 1:
            log.warning("More than one DNS type specified for testing. " +
                        "Testing only for " + outputdnstypes[0])
            outputdnstype = outputdnstypes[0]
        elif len(outputdnstypes) == 0:
            log.warning("No test type specified for DNS test. " +
                        "Testing for A record.")
            outputdnstype = "A"
        elif len(outputdnstypes) == 1:
            outputdnstype = outputdnstypes[0]

        sport = int(sc.RandNum(1024, 65535))
        # start sniffer thread
        if "pcap" in output:
            # build lfilter
            lfilter = lambda (p): (p.dport and p.dport == port or
                                   p.sport and p.sport == port)
            sniffer = SnifferThread(l2socket=sc.conf.L2socket,
                                    lfilter=lfilter,
                                    count=mincount,
                                    timeout=timeout)
            sniffer.setDaemon(True)
            sniffer.start()

        # run the m'fing query
        # TODO: ADD DNSSEC
        r1, r2, a1, a2 = dresolver.query(domain,
                                         outputdnstype, source_port=sport,
                                         want_dnssec=dnssec, tcp=tcp,
                                         wait_for_second=wait_for_second)
        resultanswers = []  # list of returned records

        # find out whether the response contains what we're looking for
        for i, (r, a) in enumerate([(r1, a1), (r2, a2)]):
            foundanswer = False
            if a == "ok":
                for answer in r.response.answer:
                    # if we found what we're looking for, store it.
                    if answer.rdtype == dns.rdatatype._by_text[outputdnstype]:
                        resultanswers.append(answer)
                        foundanswer = True
                # if we found an answer, loop through the result rrsets and
                # store them.
                if foundanswer:
                    # take the ACTUAL results and put them in a list
                    answerstrings = []
                    for answer in resultanswers:
                        for record in answer:
                            answerstrings.append(record.to_text())
                    result[outputdnstype + str(i + 1) + "list"] = \
                        ",".join(answerstrings)
                    result[outputdnstype + str(i + 1)] = answerstrings[0]
                    log.debug(outputdnstype + str(i + 1) +
                              "list: " + ",".join(answerstrings))
                    log.debug(outputdnstype + str(i + 1) +
                              ": " + answerstrings[0])
                # if we didn't find any answers, go through them again
                # and look for CNAMES
                elif not foundanswer:
                    for answer in r.response.answer:
                        if answer.rdtype == 5:  # if we found a CNAME record
                            # now we have to call the function again.
                            # this is a bit dangerous because the order of
                            # incoming replies could be reversed (if we're
                            # doing wait_for_second=1), and we could
                            # inadvertently test the wrong thing. But save from
                            # storing everything, there isn't really a way to
                            # avoid that.
                            cresult = \
                                PonyFunctions.pony_dns(outputdnstype,
                                                       answer[0].to_text(),
                                                       dnssec=dnssec,
                                                       tcp=tcp,
                                                       wait_for_second=
                                                       wait_for_second)
                            result[outputdnstype + str(i + 1)] = \
                                cresult[outputdnstype + str(i + 1)]
                            result[outputdnstype + str(i + 1) + "list"] = \
                                cresult[outputdnstype + str(i + 1) + "list"]
                            foundanswer = True

            else:  # if result wasn't okay
                log.debug("No result for " + outputdnstype + str(i + 1))
                result[outputdnstype + str(i + 1) + "list"] = ""
                result[outputdnstype + str(i + 1)] = a
        # get sniff result
        if "pcap" in output:
            sniffer.stop()
            sniffer.join()
            pcap = sniffer.getPacketList()
            if pcap:
                pcapw = pcapwriter.PcapWriter(sc.conf.l2types)
                pcapw.write(pcap)
                result["pcap"] = pcapw.getBase64String()
            else:
                result["pcap"] = ""

        # get answer
        # based on what the querytype is
        # based on whether dnssec worked.
        return result

    @staticmethod
    def pony_gethttp(output, scheme, domain, path, host, timeout=5,
                     headers="", verifyhttps=False):
        """Performs a HTTP GET request on the given URL.

        :param output: comma-separated string
        :param scheme: the URL scheme (protocol). Typically, the `$SCHEME`
          placeholder can be used in experiment specifications.
        :param domain: the domain to be used.
          The `$FQDN` placeholder can be used
          in experiment specifications, but it often makes sense to use
          the IP address of the website as returned by a previous DNS
          query.
        :param path: the path on the server. For example, if the page to be
          retrieved is located at `www.example.com/pages/page1.html`, then
          `/pages/page1.html` would be the path. The `$PATH` placeholder can be
          used in experiment specifications.
        :param host: the domain used in the `Host` HTTP header. A host should
          be specified either in this parameter or as part of the `headers`
          string when an IP address is used for the `domain` parameter. If no
          host header is specified (which is only allowed in the deprecated
          HTTP 1.0), the server may not know which page to server if multiple
          virtual hosts are associated with the same IP address. If
          different host names are specified in the `host` parameter
          and in the `headers` parameter, the name in the `host` parameter is
          used.
        :param timeout: the time, in seconds, to wait for a response
          from the server.
        :param headers: specifies HTTP headers to send
          with the request, where a header is composed of the field name,
          followed by a colon, followed by the field value. Headers are
          delimited by newline characters (``"\\n"``). An example would
          be ``"Accept-Language:en-US\\nUser-Agent:Mozilla/5.0 (X11; Linux
          x86_64; rv:12.0) Gecko/20100101 Firefox/21.0"``, which tells the
          server that we're requesting content delivered in US English and for
          Firefox 21. Wikipedia has a list of `HTTP request header fields
          <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields#Requests>`_
          for reference.
        :param verifyhttps: If set to :token:`True`, the client will
          attempt to verify the host's HTTPS certificate.
        """
        result = dict()
        requestLog = []  # this is where redirects, errors etc. go

        if headers:
            headers = [h.split(":", 1) for h in headers.split("\n")]
            headers = {k: v for [k, v] in headers}
        else:
            headers = dict()

        if "pcap" in output:
                # build lfilter
                sniffer = SnifferThread(l2socket=sc.conf.L2socket,
                                        lfilter=(lambda x: True),
                                        count=0,
                                        timeout=0)
                sniffer.setDaemon(True)
                sniffer.start()

        if host != "":
            headers['host'] = host
        if path is None:
            path = ""
        url = scheme + domain + path
        # Get the HTTP response. If it's a redirect, try again with the new
        # location. This is a bit tricky, because if we called this function
        # with the second response to our DNS query (i.e. if injection
        # happened), then the redirect will kill that since it's URL-based and
        # not IP based and therefore automatically resolved. We could perform
        # another DNS query for every redirect, and then store both results,
        # but with an increasing number of redirects that opens up a big
        # exponential rabbit hole. So, CAVEAT USER!
        while(True):
            try:
                r = requests.get(url, headers=headers,
                                 verify=verifyhttps, allow_redirects=False,
                                 timeout=timeout)
            except requests.ConnectionError:
                # if it didn't work, log an error and an empty result
                log.debug("HTTPget warning: Cannot access " + url)
                requestLog.append("Connection error: " + url)
                r = requests.Request
                r.status_code = 0
                r.content = ""
                r.headers = dict()
            except requests.Timeout:
                # if it didn't work, log an error and an empty result
                log.debug("HTTPget warning: Timed out accessing " + url)
                requestLog.append("Timeout error: " + url)
                r = requests.Request
                r.status_code = 0
                r.content = ""
                r.headers = dict()
            except Exception as e:
                # another error? oh boy.
                log.debug("HTTPget warning: error encountered accessing "
                          + url + " (" + str(e) + ")")
                requestLog.append("Other error: " + url + " (" + str(e) + ")")
                r = requests.Request
                r.status_code = 0
                r.content = ""
                r.headers = dict()

            if 300 <= r.status_code <= 310:
                newlocation = r.headers['location']
                if newlocation.startswith('//'):
                    parsed_url = urlparse.urlparse(r.url)
                    url = '%s:%s' % (parsed_url.scheme, newlocation)

                if '://' in newlocation:
                    scheme, uri = newlocation.split('://', 1)
                    url = '%s://%s' % (scheme.lower(), uri)

                if not urlparse.urlparse(newlocation).netloc:
                    # if just the path got replaced, host header stays
                    url = urlparse.urljoin(r.url, requote_uri(newlocation))
                else:
                    url = requote_uri(newlocation)
                    headers = {"host": urlparse.urlparse(url).netloc}

                log.debug("HTTPget warning: " + host + " is a redirect to " +
                          url + ". Following ...")
                requestLog.append("Redirection to: " + url)
                continue
            else:
                break

        # get sniff result
        if "pcap" in output:
            sniffer.stop()
            sniffer.join()
            pcap = sniffer.getPacketList()
            if pcap:
                pcapw = pcapwriter.PcapWriter(sc.conf.l2types)
                pcapw.write(pcap)
                result["pcap"] = pcapw.getBase64String()
            else:
                result["pcap"] = ""

        encoded_content = get_unicode_from_response(r)

        addresult(output, result, "httpcontent", encoded_content)
        addresult(output, result, "httpstatus", r.status_code)
        addresult(output, result, "httpheaders", "\n".join([k + ":" + v
                                                            for (k, v) in
                                                            r.headers.items()
                                                            ]))
        addresult(output, result, "httplog", "\n".join(requestLog))

        return result

    @staticmethod
    def pony_echo(output, string):
        result = dict()
        result['echo'] = string
        return result
