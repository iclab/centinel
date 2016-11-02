'''
#######################################################################################################
#######################################################################################################
Arash Molavi Kakhki (arash@ccs.neu.edu)
Northeastern University

Goal: client replay script

Usage:
    python replay_client.py --serverInstance=[] --pcap_folder=[]

Mandatory arguments:
    pcap_folder: This is the folder containing parsed files necessary for the replay
    
    serverInstance: This is the name of the machine that's running replay server script.
              It should be added to Instance() class in python_lib.py
    
Optional arguments:
    
    tcpdump_int: This is the interface which tcpdump runs on. 
                 Mandatory if doTCPDUMP=True
    
    doTCPDUMP: set to True if you want to run tcpdump on client side
    
    publicIP: This is the public IP of the client. It's only important when the client has multiple IP
              addresses and --multipleInterface=True. Default is ''.
              Mandatory if --multipleInterface=True.
    
    iperf: if True, runs an iperf test before replay.
    
    result: if True, receives results from server at the end of replay --> currently server has no results,
            so if True, server just send a dummy file.
    
    jitter: if True, sends jitter info to server once replay is done.
    
    multipleInterface: see above.
    
    serialize: parser serialized client/server object using both pickle and JSON.
            This tells the client which one to use. Apparantly for the android app
            we need to use JSON.
    
    resultsFolder: the folder where all tcpdump and jitter files are stored in.
    
    jitterFolder: the folder made inside resultsFolder to store jitter files.
    
    tcpdumpFolder: the folder made inside resultsFolder to store tcpdump files.  
    
Do not change:
    sidechannel_port: the port that servers side channel is running on.
            ONLY change this if you've changed it on the server side. Otherwise client won't 
            be able to contact the server.
    
    timing: if True, client preserves inner packet timing when sending out packets to server.
            Server uses gevent, meaning overwhelming the server can cause bad behavior.
            Need more testing to see if it's ok to set timing to False.

IMPORTANT!!! KNOWN ISSUE:
    multipleInterface should always be false when doing tests over VPN, otherwise it goes 
    around the VPN (this is at least the case in Mac OS X)
    
    Solutions:
        1- Set --multipleInterface=False (--publicIP does not matter anymore)
        2- Make sure python picks the intended interface by:
            i)  disconnecting all other interfaces, or
            ii) change the interfaces order in Network Preferences and have your intended
                interface rank one, so the kernel picks it.
                
                
Exit codes:
    0:    Finished successfully with no errors 
    1:    maxIdleTime has reached (i.e. there hasn't been any packet send/recv activity on any socket for maxIdleTime secs)
    2:    IP flipping occurred
    
#######################################################################################################
#######################################################################################################
'''

import sys, commands, socket, time, numpy, threading, select, pickle, Queue
from python_lib import *

DEBUG = 4

activityQ = Queue.Queue()
errorQ    = Queue.Queue()

def getIPofInterface(interface, VPN=False):
    if VPN:
        interface = 'tun0'
    
    output = commands.getoutput('ifconfig')
    lines  = output.split('\n')
    
    for i in range(len(lines)):
        if lines[i].startswith(interface+':'):
            break
    
    l = lines[i+3].strip()
    assert( l.startswith('inet') )

    return l.split(' ')[1]

class ReplayObj(object):
    def __init__(self, id, replay_name, ip, tcpdump_int, realID, incomingTime=None, dumpName=None, testID=None):
        self.id           = id
        self.replay_name  = replay_name
        self.ip           = ip
        self.realID       = realID
        self.ports        = []
        self.startTime    = time.time()
        self.dumpName     = dumpName
        self.testID       = testID
        self.dump         = tcpdump(dump_name=self.dumpName, interface=tcpdump_int)
        self.exceptions   = 'NoExp'
        
        if incomingTime is None:
            self.incomingTime = time.strftime('%Y-%b-%d-%H-%M-%S', time.gmtime())
        else:
            self.incomingTime = incomingTime
    
    def get_info(self):
        return [self.incomingTime, self.realID, self.id, self.ip, self.replay_name, self.testID, self.exceptions]
    
    def get_ports(self):
        return self.id + '\t' + ';'.join(self.ports)

class tcpClient(object):
    def __init__(self, dst_instance, csp, replayName, publicIP, buff_size=4096):
        self.dst_instance = dst_instance
        self.csp          = csp
        self.replayName   = replayName
        self.publicIP     = publicIP
        self.buff_size    = buff_size
        self.addHeader    = Configs().get('addHeader')
        self.sock         = None
        self.event        = threading.Event()
        self.event.set()    #This is necessary so all clients are initially marked as ready
        
    def _connect_socket(self):
        '''
        Create and connect TCP socket
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((Configs().get('publicIP'), 0))
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect(self.dst_instance)
        
    def single_tcp_request_response(self, tcp, send_event, tolerance=100):
        '''
        Steps:
            1- Create the socket if it hasn't been created yet.
               Note that identifying happens automatically after socket creation.
            2- Send out the payload.
            3- Set send_event to notify you are done sending/
            4- Receive response (if any) --> this is based on the length of the response.
            5- Set self.event to notify you are done receiving.
        '''
        if self.sock is None:
            self._connect_socket()
            addInfo = True
        else:
            addInfo = False
        
        if addInfo and self.addHeader:
            if self.replayName.endswith('-random'):
                info = 'X-rr;{};{};{};X-rr'.format(self.publicIP, name2code(self.replayName, 'name'), self.csp)
                tcp.payload = info + tcp.payload[len(info):]
                
            elif tcp.payload[:3] == 'GET':
                tcp.payload = (  tcp.payload.partition('\r\n')[0] 
                               + '\r\nX-rr: {};{};{}\r\n'.format(self.publicIP, name2code(self.replayName, 'name'), self.csp) 
                               + tcp.payload.partition('\r\n')[2])
            
        try:
            self.sock.sendall(tcp.payload)
            activityQ.put(1)
        except:
            print "\n\nUnexpected error happened 1:", sys.exc_info()[1], tcp.c_s_pair
            send_event.set()
            self.event.set()
            return
        
        send_event.set()
        
        buffer_len = 0
        
        while tcp.response_len > buffer_len:
            
            if tcp.response_len - buffer_len < tolerance:
                r, w, e = select.select([self.sock], [], [], 0.01)
                
                if r:
                    data = self.sock.recv( min(self.buff_size, tcp.response_len-buffer_len) )
                    buffer_len += len(data)
                
                if tcp.response_len - buffer_len > 0:
                    print '\nBREAKING EARLY:', tcp.response_len - buffer_len, tcp.c_s_pair
                
                break

            else:
                try:
                    data = self.sock.recv( min(self.buff_size, tcp.response_len-buffer_len) )
                    
                    #If socket.recv returns an empty string, that means the peer (i.e. replay_server)
                    #has closed the connection or some error has happened! The following if lets the
                    #replay proceed, but the replay results might not be acceptable !
                    #Need to figure out a better way to deal with this !
                    if len(data) == 0:
                        print "\n\nUnexpected error happened 2:", sys.exc_info()[1], tcp.c_s_pair
                        break
                    
                    activityQ.put(1)
                    
                    try:
                        if data[:12] == 'WhoTheFAreU?':
                            flippedIP = data[13:]
                            errorQ.put( ('ipFlip', flippedIP, self.dst_instance) )
                    except:
                        pass
    
                except:
                    print "\n\nUnexpected error happened 3:", sys.exc_info()[1], tcp.c_s_pair
                    self.event.set()
                    return
                
                buffer_len += len(data)
            
        self.event.set()

class udpClient(object):
    def __init__(self):
        self.sock = None
        
    def create_socket(self):
        '''
        Creates UDP socket and force it to bind to a port by sending a dummy packet
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((Configs().get('publicIP'), 0))
        self.port = str(self.sock.getsockname()[1]).zfill(5)
        
    def send_udp_packet(self, udp, dstAddress):
        self.sock.sendto(udp.payload, dstAddress)
        activityQ.put(1)
        if DEBUG == 2: print "sent:", udp.payload     , 'to', dstAddress, 'from', self.sock.getsockname()
        if DEBUG == 3: print "sent:", len(udp.payload), 'to', dstAddress, 'from', self.sock.getsockname()

class Sender(object):
    '''
    This class is responsible for sending out the queue of packets (generated by the parser).
    '''
    def __init__(self):
        self.send_event  = threading.Event()
        self.sent_jitter = []
        
    def run(self, Q, clientMapping, udpSocketList, udpServerMapping, timing):
        progress_bar          = print_progress(len(Q))
        self.timing           = timing
        self.clientMapping    = clientMapping
        self.udpServerMapping = udpServerMapping
        self.time_origin      = time.time()
        self.jitterTimeOrigin = time.time()
        threads               = []
        
        udpCount = 0
        tcpCount = 0
        
        for p in Q:
            if DEBUG == 4: progress_bar.next()
            '''
            For every TCP packet:
                1- Determine on which client is should be sent out.
                2- Wait until client.event is set --> client is not receiving a response.
                3- Send tcp payload [and receive response] by calling self.next().
                4- Wait until send_event is set --> sending is done.
            
            Finally, make sure all sending/receiving threads are done before returning.
            '''
            
            try:
                p.response_len
            except AttributeError:
                self.nextUDP(p, udpSocketList)
                udpCount += 1
                continue
            
            tcpCount += 1
            
            client = self.clientMapping['tcp'][p.c_s_pair]
            
#             if p.c_s_pair not in [ '010.011.004.003.59467-004.053.056.077.00080', '010.011.004.003.59469-004.053.056.077.00080']:
#                 continue
            
#             if client.dst_instance[1] == 443:
#                 continue
            
            client.event.wait()
            client.event.clear()
            
            threads.append(self.nextTCP(client, p))
            
            self.send_event.wait()
            self.send_event.clear()
        
        map(lambda x: x.join(), threads)
        
        PRINT_ACTION('Done sending! (sent TCP: {}, UDP: {} packets)'.format(tcpCount, udpCount), 1, action=False)
        
    def nextTCP(self, client, tcp):
        '''
        It fires off a thread to sends a single tcp packet and receive it's response.
        It returns the thread handle. 
        '''
        if self.timing:
            try:
                time.sleep((self.time_origin + tcp.timestamp) - time.time())
            except:
                pass
            
        t = threading.Thread(target=client.single_tcp_request_response, args=(tcp, self.send_event,))
        t.start()
        
        return t
    
    def nextUDP(self, udp, udpSocketList):
        clientPort = udp.c_s_pair[16:21]
        dstIP      = udp.c_s_pair[22:-6]
        dstPort    = udp.c_s_pair[-5:]
        dstAddress = self.udpServerMapping[dstIP][dstPort]
        client     = self.clientMapping['udp'][clientPort]

        if client.sock is None:
            client.create_socket()
            udpSocketList.append(client.sock)
            
        if self.timing:
            try:
                time.sleep((self.time_origin + udp.timestamp) - time.time())
            except:
                pass
        
        currentTime = time.time()
        self.sent_jitter.append( (str(currentTime - self.jitterTimeOrigin), udp.payload) )
        self.jitterTimeOrigin = currentTime
        
        client.send_udp_packet(udp, dstAddress)
        
class Receiver(object):
    def __init__(self, buff_size=4096):
        self.buff_size   = buff_size
        self.keepRunning = True
        self.rcvd_jitter = []
    
    def run(self, udpSocketList):
        
        self.jitterTimeOrigin = time.time()
        
        count = 0

        while self.keepRunning is True:
            r, w, e = select.select(udpSocketList, [], [], 0.1)
            for sock in r:
                
                (data, address) = sock.recvfrom(self.buff_size)
                activityQ.put(1)
                count += 1
                
                currentTime = time.time()
                self.rcvd_jitter.append( (str(currentTime - self.jitterTimeOrigin), data) )
                self.jitterTimeOrigin = currentTime
                
                if DEBUG == 2: print '\tGot: ', data
                if DEBUG == 3: print '\tGot: ', len(data), 'on', sock.getsockname(), 'from', address
                
        PRINT_ACTION('Done receiving! (received {} UDP packets)'.format(count), 1, action=False)
        
class SideChannel(object):
    '''
    Client uses SideChannel to:
        0- Initiate SideChannel connection
        1- Identify itself to the server (by sending id;replayName)
        2- Receive port mapping from the server (so it know what each original csp has been mapped to on the server)
        3- Request and receive results (once done with the replay)
        4- At this point, the server itself will close the connection
    '''
    def __init__(self, instance, buff_size=4096):
        self.instance    = instance
        self.buff_size   = buff_size
        self.doneSending = False
        self.monitor     = True

        self.sock        = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((Configs().get('publicIP'), 0))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.connect(self.instance)
        
    def activityMonitor(self, actQ, errQ, maxIdleTime, replayObj):
        '''
        This function monitors the replay process and kills if necessary.
        
        '''
        latestActivity = time.time()
        
        exitCode = 0
        
        while self.monitor:
            try:
                actQ.get(timeout=0.1)
                latestActivity = time.time()
            except:
                inactiveTime = time.time() - latestActivity
                if inactiveTime > maxIdleTime:
                    exitCode = 1
                    break
            
            try:
                data = errQ.get(block=False)
                if data[0] == 'ipFlip':
                    exitCode = 2
                    flippedIP   = data[1]
                    dstInstance = data[2]
                break
            except Queue.Empty:
                pass
        
        if exitCode == 1:
            print '\n\n*****Too much idle time! Killing the replay {}*****\n\n'.format(inactiveTime)
            self.send_object('timeout')
        elif exitCode == 2:
            print '\n\n*****IP flipping detected (sideChannel: {}, flipped:{}, destination: {})*****\n\n'.format(self.publicIP, flippedIP, dstInstance)
            self.send_object('ipFlip')

        if Configs().get('doTCPDUMP'):
            replayObj.dump.stop()
            
        if exitCode != 0:
            os._exit(exitCode)
      
    def sendIperf(self):
        iperfRate = None
        
        if Configs().get('iperf'):
            self.send_object('WillSendIperf')
            
            command   = ['iperf', '-c', Configs().get('serverInstanceIP')]
            
            if Configs().get('multipleInterface') is True:
                command += ['-B', Configs().get('publicIP')]
            
            iperfRes  = subprocess.check_output(command)
            iperfRate = ' '.join(iperfRes.strip().rpartition('\n')[2].strip().split()[-2:])
            
            PRINT_ACTION('result: '+iperfRate, 1, action=False)
            
            self.send_object(iperfRate)
        
        else:
            PRINT_ACTION('No iperf', 1, action=False)
            self.send_object('NoIperf')
    
    def sendMobileStats(self, mobileStats):
        if mobileStats is None:
            self.send_object('NoMobileStats')
        else:
            self.send_object('WillSendMobileStats')
            self.send_object(mobileStats)
        
    def identify(self, replayName, endOfTest, extraString='extraString', size=10):
        extraString = extraString.replace('_', '-')
        
        permaData         = PermaData()
        self.id           = permaData.id
        self.historyCount = permaData.historyCount
        self.send_object(';'.join([self.id, Configs().get('testID'), replayName, str(extraString), str(self.historyCount), str(endOfTest)]))
        
        if Configs().get('byExternal') is False:
            permaData.updateHistoryCount()
        
    def ask4Permision(self):
        return self.receive_object().split(';')
    
    def notifier(self, udpSenderCount):
        '''
        Listens for incoming updates regarding server's UDP senders:
            - STARTED: id telling server it started sending to a port
            - DONE:    id telling server it's done sending to a port
        
        It only stops when the Sender thread is done (so no new server 
        sender will be triggered) and no server UDP sender is still 
        sending (i.e., inProcess == 0) 
        '''
        inProcess = 0
        total     = 0
        while True:
            r, w, e = select.select([self.sock], [], [], 0.1)
            if r:
                data = self.receive_object().split(';')
                if data[0] == 'STARTED':
                    inProcess += 1
                    total     += 1
                elif data[0] == 'DONE':
                    inProcess -= 1
                else:
                    print 'WTF???'
                    sys.exit()
                
            if self.doneSending is True:
                if inProcess == 0:
                    PRINT_ACTION('Done notifier! ({}/{})'.format(total, udpSenderCount), 1, action=False)
                    break
    
    def receive_server_port_mapping(self):
        data = self.receive_object()
        if not data:
            return False
        mapping = json.loads(data)
        
        #convert lists to tuples (json serialization does not preserve tuples)
        for protocol in mapping:
            for ip in mapping[protocol]:
                for port in mapping[protocol][ip]:
                    mapping[protocol][ip][port] = tuple(mapping[protocol][ip][port])
                
        return mapping

    def receive_sender_count(self):
        data = self.receive_object()
        if not data:
            return False
        return int(data)
    
    def sendDone(self, duration):
        self.send_object('DONE;'+duration)

    def send_jitter(self, id, sent_jitter, rcvd_jitter, jitter=False):
        '''
        It's important to wait for server's confirmation.
        In poor networks, it might take long for jitter data to reach the server, and
        if we don't wait for confirmation, client will quit before the server does,
        and can result in permission deny by server when doing back2back replays. 
        '''
        if not jitter:
            PRINT_ACTION('NoJitter', 1, action=False)
            self.send_object(';'.join(['NoJitter', id]))
        
        else:
            self.send_object(';'.join(['WillSendClientJitter', id]))
    
            sent_jitter_file = Configs().get('jitterFolder') + '/client_sent_jitter_'+ Configs().get('dumpName') +'.txt'
            rcvd_jitter_file = Configs().get('jitterFolder') + '/client_rcvd_jitter_'+ Configs().get('dumpName') +'.txt'
            
            with open(sent_jitter_file, 'w') as f:
                sent_jitter_hashed = map(lambda j: j[0]+'\t'+str(java_byte_hashcode(j[1])), sent_jitter)
                f.write('\n'.join(sent_jitter_hashed))
            
            with open(rcvd_jitter_file, 'w') as f:
                rcvd_jitter_hashed = map(lambda j: j[0]+'\t'+str(java_byte_hashcode(j[1])), rcvd_jitter)
                f.write('\n'.join(rcvd_jitter_hashed))
                
            self.send_object(open(sent_jitter_file, 'rb').read())
            self.send_object(open(rcvd_jitter_file, 'rb').read())
        
        data = self.receive_object()
        assert(data == 'OK')
        
        return
        
    def get_result(self, outfile=None, result=False):
        '''
        It's important to wait for server's confirmation when no result is required.
        In poor networks, it might take long for 'Result;No' to reach the server, and
        if we don't wait for confirmation, client will quit before the server does,
        and can result in permission deny by server when doing back2back replays. 
        '''
        if result is False:
            self.send_object('Result;No')
            data = self.receive_object()
            assert(data == 'OK')
            return None
        
        else:
            self.send_object( 'Result;Yes' )
            data = self.receive_object()
            if outfile is not None:
                f = open(outfile, 'wb')
                f.write(data)
            return data
    
    def send_object(self, message, obj_size_len=10):
        self.sock.sendall(str(len(message)).zfill(obj_size_len))
        self.sock.sendall(message)
    
    def receive_object(self, obj_size_len=10):
        object_size = int(self.receive_b_bytes(obj_size_len))
        return self.receive_b_bytes(object_size)
    
    def receive_b_bytes(self, b):
        data = ''
        while len(data) < b:
            data += self.sock.recv( min(b-len(data), self.buff_size) )
        return data
    
    def terminate(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    
def load_Q(serialize='pickle', skipTCP=False):
    '''
    This loads and de-serializes all necessary objects.
    
    NOTE: the parser encodes all packet payloads into hex before serializing them.
          So we need to decode them before starting the replay, hence the loop at
          the end of this function.
    '''
    for file in os.listdir(Configs().get('pcap_folder')):
        if file.endswith('_client_all.' + serialize):
            pickle_file = os.path.abspath(Configs().get('pcap_folder')) + '/' + file
            break
    
    if serialize == 'pickle':
        print pickle_file
        Q, udpClientPorts, tcpCSPs, replayName = pickle.load(open(pickle_file, 'r'))
    elif serialize == 'json':
        Q, udpClientPorts, tcpCSPs, replayName = json.load(open(pickle_file, 'r'), cls=TCPjsonDecoder_client)
    
    for p in Q:
        p.payload = p.payload.decode('hex')
    
    #If skipTCP is True, clear things from tcp packets
    if skipTCP:
        tcpCSPs = []
        tmpQ    = []
        for p in Q:
            try:
                p.response_len
                continue
            except:
                tmpQ.append(p)
        Q = tmpQ
        
    #Create folder for jitter info
    if not os.path.isdir(Configs().get('pcap_folder') + '/jitter'):
        os.makedirs(Configs().get('pcap_folder') + '/jitter')
    
    return Q, udpClientPorts, tcpCSPs, replayName

def run():
    #initialSetup(pcapFolder)
    configs = Configs()
    
    PRINT_ACTION('Server IP address: {}'.format(configs.get('serverInstanceIP')), 0)
    
    PRINT_ACTION('Loading the queue', 0)
    Q, udpClientPorts, tcpCSPs, replayName = load_Q(configs.get('serialize'), skipTCP=configs.get('skipTCP'))
    
    PRINT_ACTION('Creating side channel', 0)
    sideChannel = SideChannel((configs.get('serverInstanceIP'), configs.get('sidechannel_port')))

    PRINT_ACTION('Identifying', 1, action=False)
    sideChannel.identify(replayName, configs.get('endOfTest'), extraString=configs.get('extraString'))
    PRINT_ACTION('id: {}, historyCount: {}'.format(sideChannel.id, sideChannel.historyCount), 2, action=False)
    
    PRINT_ACTION('Asking for permission', 0)
    permission = sideChannel.ask4Permision()
    if not int(permission[0]):
        if permission[1] == '1':
            PRINT_ACTION('Unknown replayName!!!', 1, action=False, exit=True)
        elif permission[1] == '2':
            PRINT_ACTION('No permission: another client with same IP address is running. Wait for them to finish!', 1, action=False, exit=False)
            os._exit(3)
    else:
        sideChannel.publicIP = permission[1]
        PRINT_ACTION('Permission granted. My public IP: {}'.format(sideChannel.publicIP), 1, action=False)
        
    PRINT_ACTION('Running iperf test', 0)
    sideChannel.sendIperf()
    
    PRINT_ACTION('Sending mobile stats', 0)
    try:
        mobileStatsFile = configs.get('mobileStats')
        with open (mobileStatsFile, "r") as f:
            mobileStats = f.read().strip()
    except:
        mobileStats = None
    
    sideChannel.sendMobileStats(mobileStats)
    
    PRINT_ACTION('Receiving server port mapping and UDP sender count', 0)
    serverMapping  = sideChannel.receive_server_port_mapping()
    udpSenderCount = sideChannel.receive_sender_count()
    for protocol in serverMapping:
        for ip in serverMapping[protocol]:
            for port in serverMapping[protocol][ip]:
                if serverMapping[protocol][ip][port][0] == '':
                    serverMapping[protocol][ip][port] = (configs.get('serverInstanceIP'), serverMapping[protocol][ip][port][1])
    
    PRINT_ACTION('Creating all TCP client sockets', 0)
    clientMapping = {'tcp':{}, 'udp':{}}
    for csp in tcpCSPs:
        dstIP        = csp.partition('-')[2].rpartition('.')[0]
        dstPort      = csp.partition('-')[2].rpartition('.')[2]
        dst_instance = serverMapping['tcp'][dstIP][dstPort]
        clientMapping['tcp'][csp] = tcpClient(dst_instance, csp, replayName, sideChannel.publicIP)
    PRINT_ACTION('Created {} TCP sockets.'.format(str(len(clientMapping['tcp']))), 1, action=False)

    PRINT_ACTION('Creating all UDP client sockets', 0)
    udpSocketList = []    
    for original_client_port in udpClientPorts:
        clientMapping['udp'][original_client_port] = udpClient()
    PRINT_ACTION('Created {} UDP sockets.'.format(str(len(clientMapping['udp']))), 1, action=False)
    
    PRINT_ACTION('Running TCPDUMP', 0)
    configs.set('dumpName', '_'.join(['client', sideChannel.id, sideChannel.publicIP, replayName, sideChannel.publicIP, time.strftime('%Y-%b-%d-%H-%M-%S', time.gmtime()), configs.get('testID'), configs.get('extraString'), str(sideChannel.historyCount), 'out']))
    if not configs.get('doTCPDUMP'):
        PRINT_ACTION('No TCPDUMP', 1, action=False)
        replayObj = None
    else:
        replayObj = ReplayObj(sideChannel.id, replayName, sideChannel.publicIP, configs.get('tcpdump_int'), sideChannel.id, dumpName=configs.get('dumpName'))
        replayObj.dump.start(host=configs.get('serverInstanceIP'))
        time.sleep(1)
    
    PRINT_ACTION('Running side channel notifier', 0)
    pNotf = threading.Thread( target=sideChannel.notifier, args=(udpSenderCount,) )
    pNotf.start()
    
    PRINT_ACTION('Running the Receiver process', 0)
    receiverObj = Receiver()
    pRecv = threading.Thread( target=receiverObj.run, args=(udpSocketList,) )
    pRecv.start()
    
    PRINT_ACTION('Running activity monitor process', 0)
    pactv = threading.Thread( target=sideChannel.activityMonitor, args=(activityQ, errorQ, configs.get('maxIdleTime'), replayObj) )
    pactv.start()
    
    PRINT_ACTION('Running the Sender process', 0)
    senderObj = Sender()
    startTime = time.time()
    pSend = threading.Thread( target=senderObj.run, args=(Q, clientMapping, udpSocketList, serverMapping['udp'], configs.get('timing'), ) )
    pSend.start()
    
    '''
    The order in following joins is very important:
        1a-Wait for sender to be done.
        1b-Wait one second in case a new server UDP sendings comes in.
        2- Let notifier thread know sending is done by setting doneSending = True.
        3- Wait for notifier: all started server UDP sendings are done.
        4- Let receiver thread know it can stop receiving.
        5- Wait for receiver thread to exit.
    '''
    pSend.join()
    time.sleep(1)
    sideChannel.doneSending = True
    pNotf.join()
    receiverObj.keepRunning = False
    pRecv.join()
    
    #Stop activityMonitor since it doesn't consider sideChannel send/recv as activity and might
    #timeout while sending jitter data.
    #We might want to change this later and have it monitor sideChannel too.
    sideChannel.monitor = False
    
    duration = str(time.time() - startTime)
    
    PRINT_ACTION('Telling server done with replaying', 0)
    sideChannel.sendDone(duration)
    
    PRINT_ACTION('Sending the jitter results on client...', 0)
    sideChannel.send_jitter(sideChannel.id, senderObj.sent_jitter, receiverObj.rcvd_jitter, jitter=configs.get('jitter'))

    PRINT_ACTION('Receiving results ...', 0)
    sideChannel.get_result('result.jpg', result=configs.get('result'))
    
    PRINT_ACTION('Fin', 0)
    PRINT_ACTION('The process took {} seconds'.format(duration), 1, action=False)
    
    return True
   
def initialSetup(pcapFolder):
    PRINT_ACTION('Reading configs file and args)', 0)
    configs = Configs()
    configs.set('sidechannel_port' , 55555)
    configs.set('serialize'        , 'pickle')
    configs.set('timing'           , True)
    configs.set('jitter'           , True)
    configs.set('doTCPDUMP'        , False)
    configs.set('result'           , False)
    configs.set('iperf'            , False)
    configs.set('multipleInterface', False)
    configs.set('resultsFolder'    , 'Results')
    configs.set('jitterFolder'     , 'jitterResults')
    configs.set('tcpdumpFolder'    , 'tcpdumpsResults')
    configs.set('extraString'      , 'extraString')
    configs.set('byExternal'       , False)
    configs.set('skipTCP'          , False)
    configs.set('addHeader'        , False)
    configs.set('maxIdleTime'      , 30)
    configs.set('endOfTest'        , True)
    configs.set('testID'           , 'SINGLE')   #options: VPN, NOVPN, RANDOM, SINGLE -- we need this for the vpn_no_vpn wrapper
    configs.set('pcap_folder'      , pcapFolder) 
    configs.set('serverInstance'   , 'server')
    configs.read_args(sys.argv)
    configs.check_for(['pcap_folder'])
    
    #The following does a DNS lookup and resolves server's IP address
    try:
        configs.get('serverInstanceIP')
    except KeyError:
        configs.check_for(['serverInstance'])
        configs.set('serverInstanceIP', Instance().getIP(configs.get('serverInstance')))
    
    if configs.get('doTCPDUMP'):
        configs.check_for(['tcpdump_int'])

    configs.show_all()

    if not configs.get('multipleInterface'):
        configs.set('publicIP', '')
    else:
        try:
            publicIPInterface = configs.get('publicIPInterface')
            configs.set('publicIP', getIPofInterface( publicIPInterface, VPN=(configs.get('testID').startswith('VPN')) ))
        except KeyError:
            configs.check_for(['publicIP'])
    
    PRINT_ACTION('Creating results folders', 0)
    if not os.path.isdir(configs.get('resultsFolder')):
        os.makedirs(configs.get('resultsFolder'))
    
    configs.set('jitterFolder', configs.get('resultsFolder') + '/' + configs.get('jitterFolder'))
    if not os.path.isdir(configs.get('jitterFolder')):
        os.makedirs(configs.get('jitterFolder'))
    
    configs.set('tcpdumpFolder', configs.get('resultsFolder') + '/' + configs.get('tcpdumpFolder'))    
    if not os.path.isdir(configs.get('tcpdumpFolder')):
        os.makedirs(configs.get('tcpdumpFolder'))
