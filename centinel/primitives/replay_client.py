'''
#######################################################################################################
#######################################################################################################
by: Arash Molavi Kakhki (arash@ccs.neu.edu)
    Northeastern University
'''

import sys, socket, numpy, threading, select, pickle, Queue, logging, multiprocessing, psutil, urllib2, urllib

import os, ConfigParser, math, json, time, subprocess, commands, random, string, logging, logging.handlers, socket, StringIO

try:
    import gevent.subprocess
except:
    import subprocess

try:
    import dpkt
except:
    pass


def getIPofInterface(interface):
    output = commands.getoutput('ifconfig')
    lines = output.split('\n')

    for i in range(len(lines)):
        if lines[i].startswith(interface + ':'):
            break

    l = lines[i + 3].strip()
    assert (l.startswith('inet'))

    return l.split(' ')[1]


class UI(object):
    '''
    This class contains all the methods to interact with the analyzerServer
    '''

    def __init__(self, ip, port):
        self.path = ('http://'
                     + ip
                     + ':'
                     + str(port)
                     + '/Results')

    def ask4analysis(self, id, historyCount):
        '''
        Send a POST request to tell analyzer server to analyze results for a (userID, historyCount)

        server will send back 'True' if it could successfully schedule the job. It will
        return 'False' otherwise.

        This is how and example request look like:
            method: POST
            url:    http://54.160.198.73:56565/Results
            data:   userID=KSiZr4RAqA&command=analyze&historyCount=9
        '''
        data = {'userID': id, 'command': 'analyze', 'historyCount': historyCount}
        res = self.sendRequest('POST', data=data)
        return res

    def getSingleResult(self, id, historyCount=None):
        '''
        Send a GET request to get result for a historyCount

        This is how an example url looks like:
            method: GET
            http://54.160.198.73:56565/Results?userID=KSiZr4RAqA&command=singleResult&historyCount=9
        '''
        data = {'userID': id, 'command': 'singleResult'}

        if isinstance(historyCount, int):
            data['historyCount'] = historyCount

        res = self.sendRequest('GET', data=data)
        return res

    def getMultiResults(self, id, maxHistoryCount=None, limit=None):
        '''
        Send a GET request to get maximum of 10 result.

        if maxHistoryCount not provided, returns the most recent results

        This is how an example url looks like:
            method: GET
            http://54.160.198.73:56565/Results?userID=KSiZr4RAqA&command=multiResults&maxHistoryCount=9
        '''
        data = {'userID': id, 'command': 'multiResults'}

        if isinstance(maxHistoryCount, int):
            data['maxHistoryCount'] = maxHistoryCount

        if isinstance(limit, int):
            data['limit'] = limit

        res = self.sendRequest('GET', data=data)
        return res

    def sendRequest(self, method, data=''):
        '''
        Sends a single request to analyzer server
        '''
        data = urllib.urlencode(data)

        if method.upper() == 'GET':
            req = urllib2.Request(self.path + '?' + data)

        elif method.upper() == 'POST':
            req = urllib2.Request(self.path, data)

        res = urllib2.urlopen(req).read()
        return json.loads(res)


def run_one(round, tries, vpn=False):
    '''
    Runs the client script once.
        - if vpn == True: use vpn, else do directly
    '''
    #if vpn:
    #    toggleVPN('connect')
    #else:
    #    toggleVPN('disconnect')

    #time.sleep(2)  # wait for VPN to toggle

    tryC = 1
    while tryC <= tries:

        startNetUsage = psutil.net_io_counters(pernic=True)

        p = multiprocessing.Process(target=run)
        p.start()
        p.join()

        endNetUsage = psutil.net_io_counters(pernic=True)

        logging.info('Done with {}. Exit code: {}'.format(Configs().get('testID'), p.exitcode))
        tryC += 1

        # If:  successful: exitCode == 0
        # or   no permission: exitCode == 3
        if p.exitcode in [0, 3]:
            break
        # If ipFlipping: exitCode == 2
        elif p.exitcode == 2:
            Configs().set('addHeader', True)
            Configs().set('extraString', Configs().get('extraString') + '-addHeader')
            logging.debug('*****ATTENTION: there seems to be IP flipping happening. Will addHeader from now on.*****')

    netStats = {}
    for interface in endNetUsage:
        netStats[interface] = {'bytesSent': endNetUsage[interface].bytes_sent - startNetUsage[interface].bytes_sent,
                               'bytesRcvd': endNetUsage[interface].bytes_recv - startNetUsage[interface].bytes_recv}

    return p.exitcode, netStats


def runSet():

    configs = Configs()
    netStats = {}

    for i in range(configs.get('rounds')):
        netStats[i + 1] = {}

        if (i == configs.get('rounds') - 1) and (not configs.get('doVPNs')) and (not configs.get('doRANDOMs')):
            configs.set('endOfTest', True)

        if configs.get('doNOVPNs'):
            configs.set('testID', 'NOVPN_' + str(i + 1))
            logging.info('DOING ROUND: {} -- {} -- {}'.format(i + 1, configs.get('testID'), configs.get('pcap_folder')))
            exitCode, netStats[i + 1]['NOVPN'] = run_one(i, configs.get('tries'), vpn=False)

            if exitCode == 3:
                raise RuntimeError('Exit code 3 in runSet')

            time.sleep(2)

        if configs.get('doRANDOMs'):

            if (i == configs.get('rounds') - 1) and (not configs.get('doVPNs')):
                configs.set('endOfTest', True)

            configs.set('testID', 'RANDOM_' + str(i + 1))

            configs.set('pcap_folder', configs.get('pcap_folder') + '_random')
            logging.info('DOING ROUND: {} -- {} -- {}'.format(i + 1, configs.get('testID'), configs.get('pcap_folder')))

            # Every set of replays MUST start with testID=NOVPN_1, this is a server side thing!
            # If NOVPN is False, we use RANDOMs are NOVPN.
            if not configs.get('doNOVPNs'):
                logging.debug('doNOVPNs is False --> changing testID from RANDOM to NOVPN for server compatibility!')
                configs.set('testID', 'NOVPN_' + str(i + 1))

            exitCode, netStats[i + 1]['RANDOM'] = run_one(i, configs.get('tries'), vpn=False)
            configs.set('pcap_folder', configs.get('pcap_folder').replace('_random', ''))
            time.sleep(2)

        if configs.get('doVPNs'):
            if i == configs.get('rounds') - 1:
                configs.set('endOfTest', True)

            configs.set('testID', 'VPN_' + str(i + 1))

            if configs.get('sameInstance'):
                serverInstanceIP = configs.get('serverInstanceIP')
                #configs.set('serverInstanceIP', Instance().getIP('VPN'))

            if configs.get('doTCPDUMP'):
                tcpdump_int = configs.get('tcpdump_int')
                configs.set('tcpdump_int', configs.get('tcpdump_int'))
            # configs.set('tcpdump_int', 'en0')
            #                 configs.set('tcpdump_int', None)

            logging.info('DOING ROUND: {} -- {} -- {}'.format(i + 1, configs.get('testID'), configs.get('pcap_folder')))
            exitCode, netStats[i + 1]['VPN'] = run_one(i, configs.get('tries'), vpn=True)

            if configs.get('sameInstance') is True:
                configs.set('serverInstanceIP', serverInstanceIP)

            if configs.get('doTCPDUMP'):
                configs.set('tcpdump_int', tcpdump_int)

        logging.info('Done with round :{}\n'.format(i + 1))


    return netStats

def PRINT_ACTION(message, indent, action=True, exit=False):
    if action:
        logging.info(''.join(['\t']*indent), '[' + str(Configs().action_count) + ']' + message)
        Configs().action_count = Configs().action_count + 1
    elif exit is False:
        logging.info(''.join(['\t']*indent) + message)
    else:
        logging.error('***** Exiting with error: *****' + message + '***********************************')
        raise RuntimeError(message)


class PermaData(object):
    def __init__(self, path='', fileName='uniqID.txt', size=10):
        if path != '':
            if not os.path.exists(path):
                os.makedirs(path)

        self.path = path + fileName

        try:
            with open(self.path, 'r') as f:
                [self.id, self.historyCount] = f.readline().split('\t')
                self.historyCount = int(self.historyCount)
        except IOError:
            self.id = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))
            self.historyCount = 0
            self._update()

    def updateHistoryCount(self):
        self.historyCount += 1
        self._update()

    def _update(self):
        with open(self.path, 'w') as f:
            f.write((self.id + '\t' + str(self.historyCount)))


def dir_list(dir_name, subdir, *args):
    '''
    Return a list of file names in directory 'dir_name'
    If 'subdir' is True, recursively access subdirectories under 'dir_name'.
    Additional arguments, if any, are file extensions to add to the list.
    Example usage: fileList = dir_list(r'H:\TEMP', False, 'txt', 'py', 'dat', 'log', 'jpg')
    '''
    fileList = []
    for file in os.listdir(dir_name):
        dirfile = os.path.join(dir_name, file)
        if os.path.isfile(dirfile):
            if len(args) == 0:
                fileList.append(dirfile)
            else:
                if os.path.splitext(dirfile)[1][1:] in args:
                    fileList.append(dirfile)
        # recursively access file names in subdirectories
        elif os.path.isdir(dirfile) and subdir:
            fileList += dir_list(dirfile, subdir, *args)
    return fileList

class UDPset(object):
    def __init__(self, payload, timestamp, c_s_pair, end=False):
        self.payload = payload
        self.timestamp = timestamp
        self.c_s_pair = c_s_pair
        self.end = end

    def __str__(self):
        return '{}--{}--{}--{}'.format(self.payload, self.timestamp, self.c_s_pair, self.end)

    def __repr__(self):
        return '{}--{}--{}--{}'.format(self.payload, self.timestamp, self.c_s_pair, self.end)


class RequestSet(object):
    '''
    NOTE: These objects are created in the parser and the payload is encoded in HEX.
          However, before replaying, the payload is decoded, so for hash and length,
          we need to use the decoded payload.
    '''

    def __init__(self, payload, c_s_pair, response, timestamp):
        self.payload = payload
        self.c_s_pair = c_s_pair
        self.timestamp = timestamp

        if response is None:
            self.response_hash = None
            self.response_len = 0
        else:
            self.response_hash = hash(response.decode('hex'))
            self.response_len = len(response.decode('hex'))

    def __str__(self):
        return '{} -- {} -- {} -- {}'.format(self.payload, self.timestamp, self.c_s_pair, self.response_len)


class ResponseSet(object):
    '''
    NOTE: These objects are created in the parser and the payload is encoded in HEX.
          However, before replaying, the payload is decoded, so for hash and length,
          we need to use the decoded payload.
    '''

    def __init__(self, request, response_list):
        self.request_len = len(request.decode('hex'))
        self.request_hash = hash(request.decode('hex'))
        self.response_list = response_list

    def __str__(self):
        return '{} -- {}'.format(self.request_len, self.response_list)


class OneResponse(object):
    def __init__(self, payload, timestamp):
        self.payload = payload
        self.timestamp = timestamp


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Configs(object):
    '''
    This object holds all configs

    BE CAREFUL: it's a singleton!
    '''
    __metaclass__ = Singleton
    _Config = None
    _configs = {}

    def __init__(self, config_file=None):
        self._Config = ConfigParser.ConfigParser()
        self.action_count = 1
        self._maxlen = 0
        if config_file != None:
            read_config_file(config_file)
        self.set('sidechannel_port', 55555)
        self.set('serialize', 'pickle')
        self.set('timing', True)
        self.set('jitter', True)
        self.set('doTCPDUMP', False)
        self.set('result', False)
        self.set('iperf', False)
        self.set('multipleInterface', False)
        self.set('resultsFolder', 'Results')
        self.set('jitterFolder', 'jitterResults')
        self.set('tcpdumpFolder', 'tcpdumpsResults')
        self.set('extraString', 'extraString')
        self.set('byExternal', False)
        self.set('skipTCP', False)
        self.set('addHeader', False)
        self.set('maxIdleTime', 30)
        self.set('endOfTest', False)
        self.set('testID', 'SINGLE')
        self.set('sameInstance', True)
        self.set('tries', 1)
        self.set('rounds', 3)
        self.set('doNOVPNs', True)
        self.set('doVPNs', False)
        self.set('doRANDOMs', True)
        self.set('ask4analysis', False)
        self.set('analyzerPort', 56565)

    def read_config_file(self, config_file):
        with open(config_file, 'r') as f:
            while True:
                try:
                    l = f.readline().strip()
                    if l == '':
                        break
                except:
                    break

                a = l.partition('=')

                if a[2] in ['True', 'true']:
                    self.set(a[0], True)
                elif a[2] in ['False', 'false']:
                    self.set(a[0], False)
                else:
                    try:
                        self.set(a[0], int(a[2]))
                    except ValueError:
                        try:
                            self.set(a[0], float(a[2]))
                        except ValueError:
                            self.set(a[0], a[2])

    def read_args(self, args):
        self.set('000-scriptName', args[0])
        for arg in args[1:]:
            a = ((arg.strip()).partition('--')[2]).partition('=')

            if a[0] == 'ConfigFile':
                self.read_config_file(a[2])

            if a[2] in ['True', 'true']:
                self.set(a[0], True)

            elif a[2] in ['False', 'false']:
                self.set(a[0], False)

            else:
                try:
                    self.set(a[0], int(a[2]))
                except ValueError:
                    try:
                        self.set(a[0], float(a[2]))
                    except ValueError:
                        self.set(a[0], a[2])
                        #         if 'ConfigFile' in self._configs:
                        #             self.read_config_file(self._configs['ConfigFile'])

    def check_for(self, list_of_mandotary):
        try:
            for l in list_of_mandotary:
                self.get(l)
        except:
            logging.error('\nYou should provide \"--{}=[]\"\n'.format(l))
            raise RuntimeError('Mandatory argument missing -' + l)

    def get(self, key):
        return self._configs[key]

    def is_given(self, key):
        try:
            self._configs[key]
            return True
        except:
            return False

    def set(self, key, value):
        if value == 'True':
            self._configs[key] = True
        elif value == 'False':
            self._configs[key] = False
        else:
            self._configs[key] = value
        if len(key) > self._maxlen:
            self._maxlen = len(key)

    def show(self, key):
        logging.debug(key, ':\t', value)

    def show_all(self):
        for key in sorted(self._configs):
            logging.debug('\t', key.ljust(self._maxlen), ':', self._configs[key])

    def __str__(self):
        return str(self._configs)

    def reset_action_count(self):
        self._configs['action_count'] = 0

    def reset(self):
        _configs = {}
        self._configs['action_count'] = 0


class tcpdump(object):
    '''
    Class for taking tcpdump

    Everything is self-explanatory
    '''

    def __init__(self, dump_name=None, targetFolder='./', interface=None):
        self._interface = interface
        self._running = False
        self._p = None
        self.bufferSize = 131072

        if dump_name is None:
            self.dump_name = 'dump_' + time.strftime('%Y-%b-%d-%H-%M-%S', time.gmtime()) + '.pcap'
        else:
            self.dump_name = 'dump_' + dump_name + '.pcap'

        self.dump_name = targetFolder + self.dump_name

    def start(self, host=None):

        command = ['tcpdump', '-nn', '-B', str(self.bufferSize), '-w', self.dump_name]

        if self._interface is not None:
            command += ['-i', self._interface]

        if host is not None:
            command += ['host', host]
        logging.debug(command)
        try:
            self._p = gevent.subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except NameError:
            self._p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self._running = True

        return ' '.join(command)

    def stop(self):
        output = ['-1', '-1', '-1']
        try:
            self._p.terminate()
            output = self._p.communicate()
            output = map(lambda x: x.partition(' ')[0], output[1].split('\n')[1:4])
        except AttributeError:
            return 'None'
        self._running = False
        return output

    def status(self):
        return self._running


def java_byte_hashcode(s):
    if len(s) == 0:
        return 0
    hashCode = 1
    for b in s:
        i = ord(b)
        if i > 127:
            i = i - 256
        hashCode = (31 * hashCode + i) & 0xFFFFFFFF
    return hashCode

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
                info = 'X-rr;{};{};{};X-rr'.format(self.publicIP, Configs().get('replayCode'), self.csp)
                tcp.payload = info + tcp.payload[len(info):]
                
            elif tcp.payload[:3] == 'GET':
                tcp.payload = (  tcp.payload.partition('\r\n')[0]
                               + '\r\nX-rr: {};{};{}\r\n'.format(self.publicIP, Configs().get('replayCode'), self.csp)
                               + tcp.payload.partition('\r\n')[2])
            
        try:
            self.sock.sendall(tcp.payload)
            activityQ.put(1)
        except:
            logging.debug("\n\nUnexpected error happened 1:" + str(sys.exc_info()[1]) + str(tcp.c_s_pair))
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
                
                #if tcp.response_len - buffer_len > 0:
                    #print '\nBREAKING EARLY:', tcp.response_len - buffer_len, tcp.c_s_pair
                
                break

            else:
                try:
                    data = self.sock.recv( min(self.buff_size, tcp.response_len-buffer_len) )
                    
                    #If socket.recv returns an empty string, that means the peer (i.e. replay_server)
                    #has closed the connection or some error has happened! The following if lets the
                    #replay proceed, but the replay results might not be acceptable !
                    #Need to figure out a better way to deal with this !
                    if len(data) == 0:
                        logging.debug("Unexpected error happened 2:" + str(sys.exc_info()[1]) + str(tcp.c_s_pair))
                        break
                    
                    activityQ.put(1)
                    
                    try:
                        if data[:12] == 'WhoTheFAreU?':
                            flippedIP = data[13:]
                            errorQ.put( ('ipFlip', flippedIP, self.dst_instance) )
                    except:
                        pass
    
                except:
                    logging.debug("Unexpected error happened 3:" + str(sys.exc_info()[1]) + str(tcp.c_s_pair))
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
        #logging.debug("sent:" + str(udp.payload) + 'to' + str(dstAddress) + 'from' + str(self.sock.getsockname()))

class Sender(object):
    '''
    This class is responsible for sending out the queue of packets (generated by the parser).
    '''
    def __init__(self):
        self.send_event  = threading.Event()
        self.sent_jitter = []
        
    def run(self, Q, clientMapping, udpSocketList, udpServerMapping, timing):
        self.timing           = timing
        self.clientMapping    = clientMapping
        self.udpServerMapping = udpServerMapping
        self.time_origin      = time.time()
        self.jitterTimeOrigin = time.time()
        threads               = []
        
        udpCount = 0
        tcpCount = 0
        
        for p in Q:
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
                
                #logging.debug('Got: ' + str(len(data)) + 'on' + str(sock.getsockname()) + 'from' + str(address))
                

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
            logging.debug('*****Too much idle time! Killing the replay {}*****\n\n'.format(inactiveTime))
            self.send_object('timeout')
        elif exitCode == 2:
            logging.debug('*****IP flipping detected (sideChannel: {}, flipped:{}, destination: {})*****\n\n'.format(self.publicIP, flippedIP, dstInstance))
            self.send_object('ipFlip')

        if Configs().get('doTCPDUMP'):
            replayObj.dump.stop()
            
        if exitCode != 0:
            raise RuntimeError('exit code not equal to 0 in activityMonitor')
      
    def sendIperf(self):
        iperfRate = None
        
        if Configs().get('iperf'):
            self.send_object('WillSendIperf')
            
            command   = ['iperf', '-c', Configs().get('serverInstanceIP')]
            
            if Configs().get('multipleInterface') is True:
                command += ['-B', Configs().get('publicIP')]
            
            iperfRes  = subprocess.check_output(command)
            iperfRate = ' '.join(iperfRes.strip().rpartition('\n')[2].strip().split()[-2:])

            self.send_object(iperfRate)
        
        else:
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
                    logging.error('Unknown code. Expected STARTED or DONE')
                    raise RuntimeError('Unknown code. Expected STARTED or DONE')
                
            if self.doneSending is True:
                if inProcess == 0:
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
    configs = Configs()
    
    Q, udpClientPorts, tcpCSPs, replayName = load_Q(configs.get('serialize'), skipTCP=configs.get('skipTCP'))

    configs.set('replayCode', configs.get('replayCodes')[replayName])

    logging.debug('Creating side channel')
    sideChannel = SideChannel((configs.get('serverInstanceIP'), configs.get('sidechannel_port')))

    sideChannel.identify(replayName, configs.get('endOfTest'), extraString=configs.get('extraString'))

    logging.debug('Asking for permission')
    permission = sideChannel.ask4Permision()
    if not int(permission[0]):
        if permission[1] == '1':
            PRINT_ACTION('Unknown replayName!!!', 1, action=False, exit=True)
        elif permission[1] == '2':
            PRINT_ACTION('No permission: another client with same IP address is running. Wait for them to finish!', 1, action=False, exit=True)
    else:
        sideChannel.publicIP = permission[1]
        PRINT_ACTION('Permission granted. My public IP: {}'.format(sideChannel.publicIP), 1, action=False)

    logging.debug('Running iperf test')
    sideChannel.sendIperf()
    
    try:
        mobileStatsFile = configs.get('mobileStats')
        with open (mobileStatsFile, "r") as f:
            mobileStats = f.read().strip()
    except:
        mobileStats = None

    logging.debug('Sending mobile stats')
    sideChannel.sendMobileStats(mobileStats)

    logging.debug('Receiving server port mapping and UDP sender count')
    serverMapping  = sideChannel.receive_server_port_mapping()
    udpSenderCount = sideChannel.receive_sender_count()
    for protocol in serverMapping:
        for ip in serverMapping[protocol]:
            for port in serverMapping[protocol][ip]:
                if serverMapping[protocol][ip][port][0] == '':
                    serverMapping[protocol][ip][port] = (configs.get('serverInstanceIP'), serverMapping[protocol][ip][port][1])

    logging.debug('Creating all TCP client sockets')
    clientMapping = {'tcp':{}, 'udp':{}}
    for csp in tcpCSPs:
        dstIP        = csp.partition('-')[2].rpartition('.')[0]
        dstPort      = csp.partition('-')[2].rpartition('.')[2]
        dst_instance = serverMapping['tcp'][dstIP][dstPort]
        clientMapping['tcp'][csp] = tcpClient(dst_instance, csp, replayName, sideChannel.publicIP)

    logging.debug('Creating all UDP client sockets')
    udpSocketList = []
    for original_client_port in udpClientPorts:
        clientMapping['udp'][original_client_port] = udpClient()

    configs.set('dumpName', '_'.join(['client', sideChannel.id, sideChannel.publicIP, replayName, sideChannel.publicIP, time.strftime('%Y-%b-%d-%H-%M-%S', time.gmtime()), configs.get('testID'), configs.get('extraString'), str(sideChannel.historyCount), 'out']))
    if not configs.get('doTCPDUMP'):
        replayObj = None
    else:
        replayObj = ReplayObj(sideChannel.id, replayName, sideChannel.publicIP, configs.get('tcpdump_int'), sideChannel.id, dumpName=configs.get('dumpName'))
        replayObj.dump.start(host=configs.get('serverInstanceIP'))
        time.sleep(1)

    logging.debug('Running side channel notifier')
    pNotf = threading.Thread( target=sideChannel.notifier, args=(udpSenderCount,) )
    pNotf.start()

    logging.debug('Running receiver process')
    receiverObj = Receiver()
    pRecv = threading.Thread( target=receiverObj.run, args=(udpSocketList,) )
    pRecv.start()

    logging.debug('Running activity monitor process')
    pactv = threading.Thread( target=sideChannel.activityMonitor, args=(activityQ, errorQ, configs.get('maxIdleTime'), replayObj) )
    pactv.start()

    logging.debug('Running the sender process')
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

    logging.debug('telling server done with replaying')
    sideChannel.sendDone(duration)

    logging.debug('sending jitter results on client')
    sideChannel.send_jitter(sideChannel.id, senderObj.sent_jitter, receiverObj.rcvd_jitter, jitter=configs.get('jitter'))

    logging.debug('Receiving results')
    sideChannel.get_result('result.jpg', result=configs.get('result'))
    

    return True
   
def initialSetup():
    configs = Configs()

    #The following does a DNS lookup and resolves server's IP address

    configs.set('serverInstanceIP', socket.gethostbyname(configs.get('serverInstanceIP')))

    if configs.get('doTCPDUMP'):
        configs.check_for(['tcpdump_int'])

    if not configs.get('multipleInterface'):
        configs.set('publicIP', '')
    else:
        try:
            publicIPInterface = configs.get('publicIPInterface')
            configs.set('publicIP', getIPofInterface( publicIPInterface, VPN=(configs.get('testID').startswith('VPN')) ))
        except KeyError:
            configs.check_for(['publicIP'])

    logging.debug('creating result folders')
    if not os.path.isdir(configs.get('resultsFolder')):
        os.makedirs(configs.get('resultsFolder'))
    
    configs.set('jitterFolder', configs.get('resultsFolder') + '/' + configs.get('jitterFolder'))
    if not os.path.isdir(configs.get('jitterFolder')):
        os.makedirs(configs.get('jitterFolder'))
    
    configs.set('tcpdumpFolder', configs.get('resultsFolder') + '/' + configs.get('tcpdumpFolder'))    
    if not os.path.isdir(configs.get('tcpdumpFolder')):
        os.makedirs(configs.get('tcpdumpFolder'))

def main():
    configs = Configs()

    ui = UI(configs.get('serverInstanceIP'), configs.get('analyzerPort'))

    initialSetup()

    netStats = {}

    netStats[1] = runSet()

    permaData = PermaData()
    diff_result = ui.getSingleResult(permaData.id, permaData.historyCount)
    permaData.updateHistoryCount()
    return diff_result
