"""
This is a fork of the RawPcapWriter/PcapWriter classes from Scapy's
utils.py module. Scapy's version writes directly to a file, whereas
we'd like to return a base64-encoded string. So this is exactly what
this thing does.
"""


import struct
import time
from scapy.base_classes import BasePacketList as bpl
import logging
from io import BytesIO
# we'll write to this like a file, then extract the string
MTU = 0x7fff  # a.k.a give me all you have
import base64


log = logging.getLogger("pony")


class RawPcapWriter:
    """A stream PCAP writer with more control than wrpcap()"""
    def __init__(self, confl2types=None, linktype=None,
                 endianness=""):
        """
        linktype: force linktype to a given value. If None, linktype is taken
                  from the first written packet
        endianness: force an endianness (little: "<", big:">").
        Default is native
        """
        self.confl2types = confl2types
        self.linktype = linktype
        self.header_present = 0
        self.endian = endianness

        self.f = BytesIO()

    def fileno(self):
        return self.f.fileno()

    def _write_header(self, pkt):
        self.header_present = 1
        self.f.write(struct.pack(self.endian + "IHHIIII", 0xa1b2c3d4L,
                                 2, 4, 0, 0, MTU, self.linktype))
        self.f.flush()

    def write(self, pkt):
        """accepts a either a single packet or a list of packets
        to be written to the dumpfile
        """
      #  log.status("Now pcaping:" + pkt.summary())
        if not self.header_present:
            self._write_header(pkt)
        if type(pkt) is str:
            self._write_packet(pkt)
        else:
            for p in pkt:
                self._write_packet(p)

    def _write_packet(self, packet, sec=None, usec=None,
                      caplen=None, wirelen=None):
        """writes a single packet to the pcap file
        """
        if caplen is None:
            caplen = len(packet)
        if wirelen is None:
            wirelen = caplen
        if sec is None or usec is None:
            t = time.time()
            it = int(t)
            if sec is None:
                sec = it
            if usec is None:
                usec = int(round((t - it) * 1000000))
        self.f.write(struct.pack(self.endian + "IIII",
                                 sec, usec, caplen, wirelen))
        self.f.write(packet)

    def flush(self):
        return self.f.flush()

    def clear(self):
        """clears the buffer completely, so it can be reused for
        the next pcap
        """
        self.f.seek(0)
        self.f.truncate(0)
        return


class PcapWriter(RawPcapWriter):
    # is invoked the same way as a RawPcapWriter:
        #confl2types=None, linktype=None,
         #        endianness=""
    # provide conf.l2types[pkt.__class__]
    def _write_header(self, pkt):
        if self.linktype is None:
            if (type(pkt) is list or type(pkt) is tuple
                    or isinstance(pkt, bpl)):
                pkt = pkt[0]
            try:
                self.linktype = self.confl2types[pkt.__class__]
        # fix this -- use conf
            except KeyError:
                log.warning("PcapWriter: unknown LL type for " +
                            pkt.__class__.__name__ +
                            ". Using type 1 (Ethernet)")
                self.linktype = 1
        RawPcapWriter._write_header(self, pkt)

    def _write_packet(self, packet):
        sec = int(packet.time)
        usec = int(round((packet.time - sec) * 1000000))
        s = str(packet)
        caplen = len(s)
        RawPcapWriter._write_packet(self, s, sec, usec, caplen, caplen)

    def getBase64String(self):
        self.flush()
        return base64.b64encode(self.f.getvalue())

    def saveToFile(self, filePath):
        with open(filePath, "wb") as outfile:
            outfile.write(self.f.getvalue())
        return
