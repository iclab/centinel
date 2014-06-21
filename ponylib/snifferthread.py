""" The SnifferThread module is used by several measurement
functions in :mod:`PonyFunctions <ponyfunctions>` to create a separate thread
that does some packet sniffing while the measurements are run.

This is done
because we're not sure if simply storing the packets returned by Scapy is good
enough---we miss some stray RST packets etc. Also, some
functions use third party libraries (e.g. :meth:`pony_dns()
<ponyfunctions.PonyFunctions.pony_dns>` uses
`dnspython <http://www.dnspython.org>`_), so we can't rely on
Scapy return values to find out
what happens at a packet level."""


from threading import Thread, Event
import time
import scapy.all as sc
import select


class SnifferThread(Thread):
    """SnifferThread is nothing but an
    asynchronous version of Scapy's sniff() function. It is loosely based
    on http://trac.secdev.org/scapy/wiki/PatchSelectStopperTimeout and
    inherits :class:`threading.Thread`.

    :param l2socket: a Scapy L2socket, as returned by ``conf.L2socket``, to be
       used to send the packets over.
    :param lfilter: a :token:`lambda` function that filters the incoming Scapy
       packets.
    :param timeout: the SnifferThread runs for at least this amount of time,
       in seconds.
    :param count: the SnifferThread runs at least long enough to capture
       this number of packets.

    Use this class as follows: instantiate and :meth:`start()
    <threading.Thread.start>` the SnifferThread,
    with the appropriate ``lfilter`` if necessary, before running the
    network measurement in question. Then, call :meth:`stop` followed
    by :meth:`join() <threading.Thread.join>`.
    Finally, retrieve captured packets by calling :meth:`getPacketList`.
    """

    def __init__(self, l2socket, lfilter, count=1, timeout=100):
        Thread.__init__(self)
        self.l2socket = l2socket
        self.lfilter = lfilter
        self.timeout = timeout
        self.isStopped = False
        self.pktCount = count
        self.stopNow = Event()
        self.hasStopped = False

    def run(self):
        """Runs the SnifferThread (called by the class's :meth:`start()
        <threading.Thread.start>` method).
        Calls the :meth:`sniff` function."""
        self.sniffed = self.sniff(self.pktCount, self.lfilter,
                                  self.l2socket, self.timeout, 1)

    def stop(self):
        """Stops the thread by triggering an event, which is polled
        by the :meth:`sniff` method's inner loop."""
        self.stopNow.set()

    def getPacketList(self):
        """Returns the list of captured packets as Scapy packet objects.
        They can then be passed to :mod:`PcapWriter <pcapwriter>` to compress
        them into a base64-encoded string."""
        return self.sniffed

    def sniff(self, count=1, lfilter=None,
              L2socket=None, timeout=None, stopperTimeout=None):
        """Implements the sniffer. This method is called by :meth:`run`."""
        c = 0

        s = L2socket(type=sc.ETH_P_ALL)

        lst = []
        stoptime = time.time() + timeout
        remain = None
        stopperStoptime = time.time() + stopperTimeout
        remainStopper = None
        while 1:
            try:
                if timeout is not None:
                    remain = stoptime - time.time()
                    if remain <= 0 and self.stopNow.isSet():
                        break

                if stopperTimeout is not None:
                    remainStopper = stopperStoptime - time.time()
                    if remainStopper <= 0:
                        if self.stopNow.isSet():
                            self.hasStopped = True
                            break
                        stopperStoptime = time.time() + stopperTimeout
                        remainStopper = stopperStoptime - time.time()

                    sel = select.select([s], [], [], remainStopper)
                    if s not in sel[0]:
                        if self.stopNow.isSet():
                            break
                else:
                    sel = select.select([s], [], [], remain)

                if s in sel[0]:
                    p = s.recv(sc.MTU, acceptOutgoing=True)
                    # fix the packet
                    # (https://github.com/jwiegley/scapy/issues/1)
                    if p.getlayer("IP"):
                        del p.getlayer("IP").len
                        del p.getlayer("IP").chksum
                    if p.getlayer("UDP"):
                        del p.getlayer("UDP").len
                    str(p)

                    if p is None:
                        continue
                    try:
                        if lfilter and not lfilter(p):
                            continue
                    # if the filter asks for something undefined
                    # in the packet, just ignore it.
                    except:
                        continue
                    lst.append(p)
                    c += 1
                    if count > 0 and c >= count:
                        break
            except KeyboardInterrupt:
                break
        s.close()
        return sc.plist.PacketList(lst, "Sniffed")
