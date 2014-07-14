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
from utils.logger import *

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
	self.client_exps = dict((c, []) for c in self.client_list)
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
		log("i", "Closing connection to the client.", address=address)
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
		    log("i", "Closing connection to the client.", address = address)
		    clientsocket.close()
        	raise Exception("Socket connection broken.")
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
	if show_progress and chunk_count:
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
	    raise Exception("Data integrity check failed.")
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
	kf = open(conf.c['public_rsa_file'])
	self.public_key = kf.read()
	kf.close()
	kf = open(conf.c['private_rsa_file'])
	self.private_key = kf.read()
	kf.close()
	
	log("i", "Sirocco server running. Awaiting connections...")

	command_thread = threading.Thread(target=self.client_command_sender, args = ())
	command_thread.daemon = True
	command_thread.start()

	try:
	    while 1:
		#accept connections from outside
		(clientsocket, address) = self.sock.accept()
		log("s", "Got a connection.", address = address)
		client_thread = threading.Thread(target=self.client_connection_handler, args = (clientsocket, address))
		client_thread.daemon = True
		client_thread.start()
	except (KeyboardInterrupt, SystemExit):
	    log("w", "Shutdown requested, shutting server down...")
	    # do some shutdown stuff, then close
	    exit(0)

    def client_command_sender(self):
	while 1:
	    com = raw_input("> ")
	    if com == "listclients":
		print bcolors.WARNING + "Connected clients: " + bcolors.ENDC
		for client, (lasttime, lastaddress) in self.client_last_seen.items():
		    if lasttime <> "":
		        if datetime.now() - lasttime < timedelta(seconds=60):
			    print bcolors.OKBLUE + "%s\t%s\t\t%s(%d seconds ago)" %(client, lastaddress, lasttime.strftime("%Y-%m-%d %H:%M:%S"), (datetime.now() - lasttime).seconds) + bcolors.ENDC
		    
		print bcolors.WARNING + "Disconnected clients: " + bcolors.ENDC
		for client, (lasttime, lastaddress) in self.client_last_seen.items():
		    if not lasttime or datetime.now() - lasttime >= timedelta(seconds=60):
		        print bcolors.FAIL + "%s\t%s\t\t%s(%s seconds ago)" %(client, lastaddress, lasttime.strftime("%Y-%m-%d %H:%M:%S") if lasttime else "never", str((datetime.now() - lasttime).seconds) if lasttime else "infinite") + bcolors.ENDC
		continue
		

	    if len(com.split()) < 2:
		print bcolors.FAIL + "No command given!" + bcolors.ENDC
		print bcolors.FAIL + "\tUsage: [client_tag | onall] [command1];[command2];..." + bcolors.ENDC
		continue
	    tag, command_list = com.split(" ", 1);
	    if tag in self.client_list and command_list <> "chill" and command_list:
		if self.client_commands[tag] == "chill":
		    self.client_commands[tag] = command_list
		else:
		    self.client_commands[tag] = self.client_commands[tag] + "; " + command_list
		log("s", "Scheduled command list \"%s\" to be run on %s. (last seen %s at %s)" %(self.client_commands[tag],tag, self.client_last_seen[tag][0], self.client_last_seen[tag][1]), tag=tag)
	    elif tag == "onall" and command_list <> "chill" and command_list:
		for client in self.client_list:
		    if self.client_commands[client] == "chill":
			self.client_commands[client] = command_list
		    else:
			self.client_commands[client] = self.client_commands[client] + "; " + command_list
		log("s", "Scheduled command list \"%s\" to be run on all clients." %(command_list))
	    else:
		log("e", "Command/client tag not recognized!")

    """
    This will handle all client requests as a separate thread.
	Clients will be authenticated and have their commands handled.
    """
    def client_connection_handler(self, clientsocket, address):
	# r: send results
	# s: sync experiments
	# b: heartbeat and get commands
	# x: close connection (can be done using "unauthorized" tag)
	# i: initialize client (can be done using "unauthorized" tag)

	# We don't want to wait too long for a response.
	clientsocket.settimeout(20)
	
	unauthorized = False
	client_tag = ""

	if not client_tag:
	    log("i", "Authenticating...", address = address)
	    try:
		client_tag = self.receive_dyn(clientsocket, address)
    
		authenticated = False

		random_token = ""
		received_token = ""
		if client_tag == "unauthorized":
		    # Only allow them to either close or initialize:
		    unauthorized = True
		elif client_tag not in self.client_list:
		    authenticated = False
		else:
		    unauthorized = False
		    random_token = self.random_string_generator(10)
    		    self.send_crypt(clientsocket, address, random_token, self.client_keys[client_tag])
		    received_token = self.receive_crypt(clientsocket, address, self.private_key, show_progress=False)

		if unauthorized or (client_tag in self.client_list and random_token == received_token):
		    if client_tag <> "unauthorized":
	    		self.send_fixed(clientsocket, address, "a")
			log("s", "Authentication successful.", address = address, tag = client_tag)
			authenticated = True
		else:
		    raise Exception("Authentication error.")
    	    except Exception as e:
	        try:
	    	    self.send_fixed(clientsocket, address, 'e')
	    	    self.send_dyn(clientsocket, address, "Authentication error.")
		except:
	    	    pass
		if clientsocket:
		    log("w", "Closing connection.", address = address, tag = client_tag)
		    clientsocket.close()
		log("e", "Authentication error: " + str(e), address=address, tag=client_tag)
		return

	outcome = True
	while outcome == True:
	    try:
		outcome = self.handle_client_requests(clientsocket, address, client_tag, unauthorized)
	    except Exception as e:
		log ("e", "Error handling client request: " + str(e), address = address, tag = client_tag)
		break
	
	# close the connection after communication ends
	if clientsocket:
	    log("w", "Closing connection.", address=address, tag=client_tag)
	    clientsocket.close()

    def handle_client_requests(self, clientsocket, address, client_tag, unauthorized = True):
	message_type = ""
	retries = 5
	while not message_type and retries > 0:
	    try:
		message_type = self.receive_fixed(clientsocket, address, 1)
	    except timeout:
		retries = retries - 1
		log("w", "Client is taking a bit too long to send command (waiting %d more cycles)... " %(retries), address = address, tag = client_tag)
	if retries == 0:
	    raise Exception("The client is not responding.")
	
	if retries < 5:
	    log("i", "Client is back online.", address = address, tag = client_tag)
    	if not unauthorized:
	    self.client_last_seen[client_tag] = datetime.now() , address[0] + ":" + str(address[1])

	# The client wants to submit results:
	if message_type == "r" and not unauthorized:
	    log("i", "Client wants to submit results.", address = address, tag = client_tag)
	    try:
    		self.send_fixed(clientsocket, address, "a")

		results_name = self.receive_dyn(clientsocket, address)
		results_decrypted = self.receive_crypt(clientsocket, address, self.private_key)

		if not os.path.exists(conf.c['results_dir']):
    		    log("i", "Creating results directory in %s" % (conf.c['results_dir']))
    		    os.makedirs(conf.c['results_dir'])

		out_file = open(os.path.join(conf.c['results_dir'],client_tag + "-" + datetime.now().isoformat() + "-" + results_name), 'w')
		out_file.write(results_decrypted)
		out_file.close()
		self.send_fixed(clientsocket, address, "a")
	    except Exception as e:
    		raise Exception("Error receiving results data: " + str(e))
	    log("s", "Results file \"%s\" received successfully." %(results_name))
	    return True

	# The client wants to end the connection.
	elif message_type == "x":
	    log("i", "Client wants to close the connection.", address = address, tag = client_tag)
	    return False

	# The client wants to initialize.
	elif message_type == "i":
	    log("i", "Client wants to initialize.", address = address)
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
	    except Exception as e:
		try:
		    self.send_fixed(clientsocket, address, "e")
		    self.send_dyn(clientsocket, address, "Initialization error.")
		except:
		    pass
		raise Exception("Initialization error: " + str(e))

	    self.client_list.append(identity)
	    self.client_keys [identity] = client_pub_key
	    self.client_last_seen [identity] = ("", "")
	    self.client_commands [identity] = "chill"
	    self.client_exps [identity] = ""
	    client_tag = identity
	    log ("s", "Client initialized successfully. New tag: " + identity, address = address, tag = client_tag)

	    # After init, the client has to disconnect and login again.
	    return False

	# The client wants to sync experiments:
	elif message_type == "s" and not unauthorized:
	    
	    try:
		client_exp_list = self.receive_crypt(clientsocket, address, self.private_key, False)
		changed = False

		if client_exp_list == "n":
		    client_exp_list = [""]
		else:
		    client_exp_list = client_exp_list.split("|")

		updates = [x for x in self.current_exp_list(client_tag) if x not in client_exp_list]

		self.send_dyn(clientsocket, address, str(len(updates)))

		for exp in updates:
		    if exp:
			changed = True
			self.sendexp(clientsocket, address, client_tag, exp.split("%")[0])

		old_list = [x.split("%")[0] for x in client_exp_list if x.split("%")[0] not in [y.split("%")[0] for y in self.current_exp_list(client_tag)] ]

		msg = ""
		for item in old_list:
		    msg += item + "|"

		if msg:
		    changed = True
		    self.send_crypt(clientsocket, address, msg[:-1], self.client_keys[client_tag])
		else:
		    self.send_crypt(clientsocket, address, "n", self.client_keys[client_tag])
	    
		if changed:
		    log("i", "Client just updated its test specs.", address = address, tag = client_tag)
	    except Exception as e:
		raise Exception("Error synchronizing experiments: " + str(e))

	    return True
	# The client is showing heartbeat:
	elif message_type == "b" and not unauthorized:
	    try:
		if self.client_commands[client_tag] == 'chill':
		    self.send_fixed(clientsocket, address, 'b')
		else:
		    self.send_fixed(clientsocket, address, 'c')
		    self.send_crypt(clientsocket, address, self.client_commands[client_tag], self.client_keys[client_tag])
		    log("i", "Client just received the latest commands.", address = address, tag = client_tag )
		    self.client_commands[client_tag] = "chill"
		return True
	    except Exception as e:
		raise Exception ("Error at heartbeat: " + str(e))
	else:
	    try:
		self.send_fixed(clientsocket, address, "e")
		self.send_dyn(clientsocket, address, "Message type not recognized.")
	    except Exception:
		pass
	    raise Exception("Message type \"%s\" not recognized." %(message_type))
	    return False

    def current_exp_list(self, client_tag):
	exp_list = list()
	exp_list += self.client_exps[client_tag]

	exp_list += [os.path.splitext(os.path.basename(path))[0] + "%" + MD5.new(open(path,'r').read()).digest() for path in glob.glob(os.path.join(conf.c['experiments_dir'], '*.cfg'))]
	return exp_list
	    
    def sendexp(self, clientsocket, address, client_tag, exp):
	f = open(os.path.join(conf.c['experiments_dir'], exp + ".cfg"), 'r')
	contents = f.read()
	self.send_dyn(clientsocket, address, exp)
	self.send_crypt(clientsocket, address, contents, self.client_keys[client_tag])

    def random_string_generator(self, size=5, chars=string.ascii_uppercase + string.digits):
	identifier = ''.join(random.choice(chars) for _ in range(size))
	while identifier in self.client_list:
	    identifier = ''.join(random.choice(chars) for _ in range(size))
	return identifier