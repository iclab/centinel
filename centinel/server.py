import math
import os
import shutil
from os import listdir
from os.path import exists,isfile, join
import StringIO
import string
import random
import gzip
import socket
import sys
import threading
import glob
from datetime import datetime
from utils.rsacrypt import RSACrypt
from Crypto.Hash import MD5
from server_config import server_conf
from utils.colors import bcolors

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

	self.client_list = [os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(conf.c['client_keys_dir'], '*'))]
	self.client_keys = dict()
	self.client_keys = dict((c, open(os.path.join(conf.c['client_keys_dir'],c), 'r').read()) for c in self.client_list)

    def send_fixed(self, clientsocket, address, data):
	try:
	    sent = clientsocket.send(data)
	except socket.error, (value,message): 
    	    if clientsocket:
		print bcolors.WARNING + "Closing connection to the client." + bcolors.ENDC
		clientsocket.close()
	    raise Exception("Could not send data to client (%s:%s): " %(address[0], address[1]) + message)
	    return False
	    
	#print "Sent %d bytes to the client." %(sent)
	return True
    
    def send_dyn(self, clientsocket, address, data):
	self.send_fixed(clientsocket, address, str(len(data)).zfill(10))
	self.send_fixed(clientsocket, address, data)
    
    def send_crypt(self, clientsocket, address, data, encryption_key):
	crypt = RSACrypt()
	crypt.import_public_key(encryption_key)

	chunk_size = 256
	chunk_count = int(math.ceil(len(data) / float(chunk_size)))
	digest = MD5.new(data).digest()

	#print bcolors.OKBLUE + "Sending %d chunks of encrypted data..." %(chunk_count) + bcolors.ENDC

	self.send_dyn(clientsocket, address, str(chunk_count))
	self.send_dyn(clientsocket, address, digest)
	
	bytes_encrypted = 0
	encrypted_data = ""
	while bytes_encrypted < len(data):
	    encrypted_chunk = crypt.public_key_encrypt(data[bytes_encrypted:min(bytes_encrypted+chunk_size, len(data))])
	    bytes_encrypted = bytes_encrypted + chunk_size
	    self.send_dyn(clientsocket, address, encrypted_chunk[0])

	#print bcolors.OKGREEN + "Encrypted data sent." + bcolors.ENDC

    def receive_fixed(self, clientsocket, address, message_len):
	chunks = []
        bytes_recd = 0
        while bytes_recd < message_len:
            chunk = clientsocket.recv(min(message_len - bytes_recd, 2048))
            if chunk == '':
                if clientsocket:
		    print bcolors.WARNING + "Closing connection to the client." + bcolors.ENDC
		    clientsocket.close()
        	raise Exception(message = "Socket connection broken (%s:%s)" %(address[0], address[1]))
		return False
	    chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
	#print ''.join(chunks)
        return ''.join(chunks)
    
    def receive_dyn(self, clientsocket, address):
	msg_size = self.receive_fixed(clientsocket, address, 10)
	msg = self.receive_fixed(clientsocket, address, int(msg_size))
	return msg

    def receive_crypt(self, clientsocket, address, decryption_key):
	crypt = RSACrypt()

	crypt.import_public_key(decryption_key)

	chunk_count = int(self.receive_dyn(clientsocket, address))
	received_digest = self.receive_dyn(clientsocket, address)

	#print bcolors.OKBLUE + "Receiving %d chunks of encrypted data..." %(chunk_count) + bcolors.ENDC

	chunk_size = 256
	decrypted_results = ""
	while chunk_count > 0:
	    encrypted_chunk = self.receive_dyn(clientsocket, address)
	    decrypted_results = decrypted_results + crypt.public_key_decrypt(encrypted_chunk)
	    chunk_count = chunk_count - 1


	#print bcolors.OKGREEN + "Encrypted data received." + bcolors.ENDC

	#print bcolors.OKBLUE + "Verifying data integrity..." + bcolors.ENDC
	calculated_digest = MD5.new(decrypted_results).digest()
	if calculated_digest == received_digest:
	    #print bcolors.OKGREEN + "Data integrity check pass." + bcolors.ENDC
	    return decrypted_results
	else:
	    print bcolors.FAIL + "Data integrity check failed." + bcolors.ENDC
	    return False

    def run(self):
	try:
	    kf = open(conf.c['public_rsa_file'])
	    self.public_key = kf.read()
	    kf.close()
	    kf = open(conf.c['private_rsa_file'])
	    self.private_key = kf.read()
	    kf.close()
	except:
	    print bcolors.FAIL + "Error loading key files."  + bcolors.ENDC
	    print bcolors.FAIL + "Exiting..." + bcolors.ENDC
	    self.connected = False
	    return False

	print bcolors.HEADER + "Server running. Awaiting connections..." + bcolors.ENDC
	while 1:
	    #accept connections from outside
	    (clientsocket, address) = self.sock.accept()
	    print bcolors.OKBLUE + "Got a connection from " + address[0] + ":" + str(address[1]) + bcolors.ENDC
	    client_thread = threading.Thread(target=self.client_connection_handler, args = (clientsocket, address))
	    client_thread.daemon = True
	    client_thread.start()

    def client_connection_handler(self, clientsocket, address):
	# r: send results
	# x: close connection
	# i: initialize client

	# We don't want to wait too long for a response.
	clientsocket.settimeout(15)
	print bcolors.OKBLUE + "Authenticating..." + bcolors.ENDC
	client_tag = self.receive_dyn(clientsocket, address)
    
	if client_tag == "unauthorized":
	    # Only allow them to either close or initialize:
	    init_only = True
	else:
	    init_only = False
	    random_token = self.random_string_generator(10)
    	    self.send_crypt(clientsocket, address, random_token, self.client_keys[client_tag])
	    received_token = self.receive_crypt(clientsocket, address, self.private_key)

	if init_only or (client_tag in self.client_list and random_token == received_token):
	    if client_tag <> "unauthorized":
		print bcolors.OKGREEN + "Authentication successful (" + client_tag + ")." + bcolors.ENDC
	else:
    	    try:
	        self.send_fixed(clientsocket, address, 'e')
	        self.send_dyn(clientsocket, address, "Authentication error.")
	    except:
	        pass
	    print bcolors.FAIL + "Authentication error (" + client_tag + ")." + bcolors.ENDC
	    return False
	self.send_fixed(clientsocket, address, "a")
	message_type = self.receive_fixed(clientsocket, address, 1)
	

	# The client wants to submit results:
	if message_type == "r" and not init_only:
	    print bcolors.OKGREEN + client_tag + "(" + address[0] + ":" + str(address[1]) + ") wants to submit results." + bcolors.ENDC
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
    		print bcolors.FAIL + client_tag + "(" + address[0] + ":" + str(address[1]) + ") error receiving data." + bcolors.ENDC
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
	    
	    self.client_connection_handler(clientsocket, address)
	    return True
	elif message_type == "x":
	    print bcolors.OKBLUE + client_tag + "(" + address[0] + ":" + str(address[1]) + ") wants to close the connection." + bcolors.ENDC
	    if clientsocket:
		print bcolors.WARNING + client_tag + "(" + address[0] + ":" + str(address[1]) + ") closing connection." + bcolors.ENDC
		clientsocket.close()
	    return True
	elif message_type == "i":
	    print bcolors.OKBLUE + "(" + address[0] + ":" + str(address[1]) + ") wants to initialize." + bcolors.ENDC
	    identity = self.random_string_generator()
	    try:
		self.send_fixed(clientsocket, address, "a")
		self.send_dyn(clientsocket, address, identity) #size is usually 5 characters (it is easy to write down and/or remember)
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
	    client_tag = identity
	    print bcolors.OKGREEN + client_tag + "(" + address[0] + ":" + str(address[1]) + ") client initialized successfully. New tag: " + identity + bcolors.ENDC

	    self.client_connection_handler(clientsocket, address)
	    return True
	else:
	    try:
		self.send_fixed(clientsocket, address, "e")
		self.send_dyn(clientsocket, address, "Message type not recognized.")
	    except Exception:
		pass
    	    if clientsocket: 
    		clientsocket.close() 
	    return False

    def random_string_generator(self, size=5, chars=string.ascii_uppercase + string.digits):
	identifier = ''.join(random.choice(chars) for _ in range(size))
	while identifier in self.client_list:
	    identifier = ''.join(random.choice(chars) for _ in range(size))
	return identifier