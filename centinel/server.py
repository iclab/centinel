import math
import time
from time import strftime
import os
import shutil
from os import listdir
from os.path import exists,isfile, join
import StringIO
import string
import random
import gzip
import socket
from socket import timeout
import sys
import threading
import glob
from datetime import datetime, timedelta
from utils.rsacrypt import RSACrypt
from Crypto.Hash import MD5
from server_config import server_conf
from utils.colors import bcolors
from utils.colors import update_progress

conf = server_conf()

class Server:
    def __init__(self, sock=None):
	if sock is None:
	    #create an INET, STREAMing socket
    	    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	else:
	    self.sock = sock
	self.sock.bind(('0.0.0.0', int(conf.c['server_port'])))
	self.sock.listen(5)
	"""
	Fill in the list of clients and their respective RSA public keys (currently read from files).
	TODO:
	Read from database.
	"""
	self.client_list = [os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(conf.c['client_keys_dir'], '*'))]
	self.client_keys = dict()
	self.client_keys = dict((c, open(os.path.join(conf.c['client_keys_dir'],c), 'r').read()) for c in self.client_list)
	self.client_commands = dict((c, "chill") for c in self.client_list)
	self.client_last_seen = dict((c, ("", "nowhere")) for c in self.client_list)
    """
    Send a string of characters on the socket.
	Size is fixed, meaning that the receiving party is 
	expected to know how many bytes to read.
    """
    def send_fixed(self, clientsocket, address, data):
	try:
	    sent = clientsocket.send(data)
	except Exception as det: 
    	    if clientsocket:
		print bcolors.WARNING + "Closing connection to the client." + bcolors.ENDC
		clientsocket.close()
	    raise Exception("Could not send data to client (%s:%s): " %(address[0], address[1])), det
	    return False
	    
	return True

    """
    Send a string of characters on the socket.
	Size is dynamic and is sent fist as a 0-padded 10-byte 
	string so that the receiving end will know how many 
	bytes to read.
    """
    def send_dyn(self, clientsocket, address, data):
	self.send_fixed(clientsocket, address, str(len(data)).zfill(10))
	self.send_fixed(clientsocket, address, data)


    """
    Send a string of characters encrpyted using a given RSA key.
	The message will be chopped up into chunks of fixed size.
	The number of encrypted chunks is sent, followed by the
	hash of the unencrypted data (used for integrity checking).
	Encrypted chunks are sent one by one after that.
    """
    def send_crypt(self, clientsocket, address, data, encryption_key):
	crypt = RSACrypt()
	crypt.import_public_key(encryption_key)

	chunk_size = 256
	chunk_count = int(math.ceil(len(data) / float(chunk_size)))
	digest = MD5.new(data).digest()

	self.send_dyn(clientsocket, address, str(chunk_count))
	self.send_dyn(clientsocket, address, digest)
	
	bytes_encrypted = 0
	encrypted_data = ""
	while bytes_encrypted < len(data):
	    encrypted_chunk = crypt.public_key_encrypt(data[bytes_encrypted:min(bytes_encrypted+chunk_size, len(data))])
	    bytes_encrypted = bytes_encrypted + chunk_size
	    self.send_dyn(clientsocket, address, encrypted_chunk[0])

    
    """
    Receive a string of characters on the socket.
	Size is fixed, meaning that we know how 
	many bytes to read.
    """
    def receive_fixed(self, clientsocket, address, message_len):
	chunks = []
        bytes_recd = 0
        while bytes_recd < message_len:
            chunk = clientsocket.recv(min(message_len - bytes_recd, 2048))
            if chunk == '':
                if clientsocket:
		    print bcolors.WARNING + "Closing connection to the client." + bcolors.ENDC
		    clientsocket.close()
        	raise Exception("Socket connection broken (%s:%s)" %(address[0], address[1]))
		return False
	    chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)
    
    """
    Receive a string of characters on the socket.
	Size is dynamic and is sent fist as a 0-padded 10-byte 
	string so that the we know how many bytes to read.
    """
    def receive_dyn(self, clientsocket, address):
	msg_size = self.receive_fixed(clientsocket, address, 10)
	msg = self.receive_fixed(clientsocket, address, int(msg_size))
	return msg

    """
    Receive a string of characters encrpyted using a given RSA key.
	The message will be received in chunks of fixed size.
	The number of encrypted chunks is received, followed by the
	hash of the unencrypted data (used for integrity checking).
	Encrypted chunks are received one by one after that and 
	decrypted using the given key. The resulting string is then
	hashed and verified using the received hash.
    """
    def receive_crypt(self, clientsocket, address, decryption_key, show_progress=True):
	crypt = RSACrypt()
	crypt.import_public_key(decryption_key)

	chunk_count = int(self.receive_dyn(clientsocket, address))
	received_digest = self.receive_dyn(clientsocket, address)

	org = chunk_count
	chunk_size = 256
	decrypted_results = ""
	if show_progress:
	    print bcolors.OKBLUE + "Progress: "
	while chunk_count > 0:
	    encrypted_chunk = self.receive_dyn(clientsocket, address)
	    decrypted_results = decrypted_results + crypt.public_key_decrypt(encrypted_chunk)
	    chunk_count = chunk_count - 1
	    if show_progress:
		update_progress( int(100 * float(org - chunk_count) / float(org)) )
	if show_progress:
	    print bcolors.ENDC


	calculated_digest = MD5.new(decrypted_results).digest()
	if calculated_digest == received_digest:
	    return decrypted_results
	else:
	    print bcolors.FAIL + "Data integrity check failed." + bcolors.ENDC
	    return False

    """
    This runs ths server daemon.
	Each connection is handled in a separate thread.
	Keyboard and system interrupts are catched and dealt with 
	to ensure smooth and clean shutdown of the server.
    """
    def run(self):
	"""
	The server will not run if the private and the public keys are 
	not read.
	"""
	try:
	    kf = open(conf.c['public_rsa_file'])
	    self.public_key = kf.read()
	    kf.close()
	    kf = open(conf.c['private_rsa_file'])
	    self.private_key = kf.read()
	    kf.close()
	except:
	    print bcolors.FAIL + "Error loading key files:" +   + bcolors.ENDC
	    print bcolors.FAIL + "Exiting..." + bcolors.ENDC
	    self.connected = False
	    return False

	print bcolors.HEADER + "Server running. Awaiting connections..." + bcolors.ENDC

	command_thread = threading.Thread(target=self.client_command_sender, args = ())
	command_thread.daemon = True
	command_thread.start()

	try:
	    while 1:
		#accept connections from outside
		(clientsocket, address) = self.sock.accept()
		print bcolors.OKBLUE + strftime("%Y-%m-%d %H:%M:%S") + ": Got a connection from " + address[0] + ":" + str(address[1]) + bcolors.ENDC
		client_thread = threading.Thread(target=self.client_connection_handler, args = (clientsocket, address, False))
		client_thread.daemon = True
		client_thread.start()
	except (KeyboardInterrupt, SystemExit):
	    print bcolors.WARNING + "Shutdown requested, shutting server down..." + bcolors.ENDC
	    # do some shutdown stuff, then close
	    exit(0)

    def client_command_sender(self):
	while 1:
	    com = raw_input("> ")
	    if len(com.split()) == 1:
		if com == "listclients":
		    print "Connected clients: "
		    for client, (lasttime, lastaddress) in self.client_last_seen.items():
			if lasttime <> "":
			    if datetime.now() - lasttime < timedelta(seconds=15):
				print "%s\t%s\t%s(%d seconds ago)" %(client, lastaddress, lasttime.strftime("%Y-%m-%d %H:%M:%S"), (datetime.now() - lasttime).seconds)
		    continue

	    if len(com.split()) < 2:
		print bcolors.FAIL + "No command given!" + bcolors.ENDC
		print bcolors.FAIL + "\tUsage: [client_tag] [command1];[command2];..." + bcolors.ENDC
		continue
	    tag, command_list = com.split(" ", 1);
	    if tag in self.client_list and command_list <> "chill" and command_list:
		if self.client_commands[tag] == "chill":
		    self.client_commands[tag] = command_list
		else:
		    self.client_commands[tag] = self.client_commands[tag] + "; " + command_list
		print bcolors.HEADER + "Scheduled command list \"%s\" to be run on %s. (last seen %s at %s)" %(self.client_commands[tag],tag, self.client_last_seen[tag][0], self.client_last_seen[tag][1])+ bcolors.ENDC
	    else:
		print bcolors.FAIL + "Command/client tag not recognized!" + bcolors.ENDC

    """
    This will handle all client requests as a separate thread.
	Clients will be authenticated and have their commands handled.
    """
    def client_connection_handler(self, clientsocket, address, client_tag=''):
	# r: send results
	# s: sync experiments
	# b: heartbeat and get commands
	# x: close connection (can be done using "unauthorized" tag)
	# i: initialize client (can be done using "unauthorized" tag)

	# We don't want to wait too long for a response.
	clientsocket.settimeout(15)
	
	init_only = False

	if not client_tag:
	    print bcolors.OKBLUE + "Authenticating..." + bcolors.ENDC
	    client_tag = self.receive_dyn(clientsocket, address)
    
	    if client_tag == "unauthorized":
		# Only allow them to either close or initialize:
		init_only = True
	    else:
		init_only = False
		random_token = self.random_string_generator(10)
    		self.send_crypt(clientsocket, address, random_token, self.client_keys[client_tag])
		received_token = self.receive_crypt(clientsocket, address, self.private_key, show_progress=False)

	    if init_only or (client_tag in self.client_list and random_token == received_token):
		if client_tag <> "unauthorized":
		    print bcolors.OKGREEN + "Authentication successful (" + client_tag + ")." + bcolors.ENDC
		    authenticated = True
	    else:
    		try:
	    	    self.send_fixed(clientsocket, address, 'e')
	    	    self.send_dyn(clientsocket, address, "Authentication error.")
		except:
	    	    pass
		print bcolors.FAIL + "Authentication error (" + client_tag + ")." + bcolors.ENDC
		return False
	    self.send_fixed(clientsocket, address, "a")
	
	message_type = ""
	retries = 5
	while not message_type and retries > 0:
	    try:
		message_type = self.receive_fixed(clientsocket, address, 1)
	    except timeout:
		retries = retries - 1
		print bcolors.WARNING + "Client is taking a bit too long to send command (retrying %d more times)... " %(retries) + bcolors.ENDC
	if retries == 0:
	    print bcolors.FAIL + strftime("%Y-%m-%d %H:%M:%S") + ": The client is not responding, closing the connection..." + bcolors.ENDC
	    if clientsocket:
		clientsocket.close()
	    return False

    	if client_tag <> "unauthorized":
	    self.client_last_seen[client_tag] = datetime.now() , address[0] + ":" + str(address[1])

	# The client wants to submit results:
	if message_type == "r" and not init_only:
	    print bcolors.OKGREEN + time.strftime("%d/%m/%Y - %H:%M:%S") + " " + client_tag + "(" + address[0] + ":" + str(address[1]) + ") wants to submit results." + bcolors.ENDC
	    try:
    		self.send_fixed(clientsocket, address, "a")

		results_name = self.receive_dyn(clientsocket, address)
		results_decrypted = self.receive_crypt(clientsocket, address, self.private_key)

		if not os.path.exists(conf.c['results_dir']):
    		    print "Creating results directory in %s" % (conf.c['results_dir'])
    		    os.makedirs(conf.c['results_dir'])

		out_file = open(os.path.join(conf.c['results_dir'],client_tag + "-" + datetime.now().time().isoformat() + "-" + results_name), 'w')
		out_file.write(results_decrypted)
		out_file.close()
	    except: 
		if clientsocket: 
    		    clientsocket.close() 
    		print bcolors.FAIL + strftime("%Y-%m-%d %H:%M:%S") + " " + client_tag + "(" + address[0] + ":" + str(address[1]) + ") error receiving data: " + sys.exc_info()[0] + bcolors.ENDC
		try:
		    self.send_fixed(clientsocket, address, "e")
		    self.send_dyn(clientsocket, address, message)
		except Exception:
		    pass
		return False

	    try:
		print bcolors.OKGREEN + client_tag + "(" + address[0] + ":" + str(address[1]) + ") results recorded." + bcolors.ENDC
		self.send_fixed(clientsocket, address, "c")
	    except Exception:
		print bcolors.FAIL + "Error sending the [complete] flag." + bcolors.ENDC
		if clientsocket:
		    print bcolors.WARNING + "Closing connection to the client." + bcolors.ENDC
		    clientsocket.close()
	    
	    self.client_connection_handler(clientsocket, address, client_tag)
	    return True

	# The client wants to end the connection.
	elif message_type == "x":
	    print bcolors.OKBLUE + client_tag + "(" + address[0] + ":" + str(address[1]) + ") wants to close the connection." + bcolors.ENDC
	    if clientsocket:
		print bcolors.WARNING + strftime("%Y-%m-%d %H:%M:%S") + " " + client_tag + "(" + address[0] + ":" + str(address[1]) + ") closing connection." + bcolors.ENDC
		clientsocket.close()
	    return True

	# The client wants to initialize.
	elif message_type == "i":
	    print bcolors.OKBLUE + strftime("%Y-%m-%d %H:%M:%S") + " (" + address[0] + ":" + str(address[1]) + ") wants to initialize." + bcolors.ENDC
	    identity = self.random_string_generator()
	    try:
		self.send_fixed(clientsocket, address, "a")
		self.send_dyn(clientsocket, address, identity) #size is usually 5 characters (it is easy to write down and/or remember)
		self.send_dyn(clientsocket, address, self.public_key)
		client_pub_key = self.receive_crypt(clientsocket, address, self.private_key)
		of = open(os.path.join(conf.c['client_keys_dir'], identity), "w")
		of.write(client_pub_key)
		of.close()
		self.send_fixed(clientsocket, address, "c")
	    except:
		print bcolors.FAIL + "Initialization unsuccessful." + bcolors.ENDC
		self.send_fixed(clientsocket, address, "e")
		self.send_dyn(clientsocket, address, "Initialization error.")
		return False

	    self.client_list.append(identity)
	    self.client_keys [identity] = client_pub_key
	    self.client_last_seen [identity] = ("", "")
	    self.client_commands [identity] = "chill"
	    client_tag = identity
	    print bcolors.OKGREEN + client_tag + "(" + address[0] + ":" + str(address[1]) + ") client initialized successfully. New tag: " + identity + bcolors.ENDC

	    self.client_connection_handler(clientsocket, address, client_tag)
	    return True

	# The client is showing heartbeat:
	elif message_type == "b" and not init_only:
	    if self.client_commands[client_tag] == 'chill':
		#print bcolors.WARNING + client_tag + " [beat]... " + bcolors.ENDC
		self.send_fixed(clientsocket, address, 'b')
	    else:
		self.send_fixed(clientsocket, address, 'c')
		self.send_crypt(clientsocket, address, self.client_commands[client_tag], self.client_keys[client_tag])
		print bcolors.WARNING + strftime("%Y-%m-%d %H:%M:%S") + " " + client_tag + " Just received the latest commands... " + bcolors.ENDC
		self.client_commands[client_tag] = "chill"

	    self.client_connection_handler(clientsocket, address, client_tag)
	else:
	    try:
		self.send_fixed(clientsocket, address, "e")
		self.send_dyn(clientsocket, address, "Message type not recognized.")
	    except Exception:
		pass
    	    if clientsocket: 
    		clientsocket.close() 
	    return False
	# The client wants to sync experiments:
	#elif message_type == "s" and not init_only:
	    

    def random_string_generator(self, size=5, chars=string.ascii_uppercase + string.digits):
	identifier = ''.join(random.choice(chars) for _ in range(size))
	while identifier in self.client_list:
	    identifier = ''.join(random.choice(chars) for _ in range(size))
	return identifier