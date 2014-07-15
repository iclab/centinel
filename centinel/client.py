import sys
sys.path.append("../")

import math
from time import gmtime, strftime
import os
import shutil
import random
import string
from os import listdir
import StringIO
import gzip
import glob
from os.path import exists,isfile, join
import socket
from utils.rsacrypt import RSACrypt
from utils.colors import bcolors
from utils.colors import update_progress
from utils.logger import *
from client_config import client_conf
from Crypto.Hash import MD5

conf = client_conf()

class ServerConnection:
    
    def __init__(self, server_address = conf.c['server_address'], server_port = int(conf.c['server_port'])):
	self.server_address = server_address
	self.server_port = server_port
	self.connected = False

	
    def connect(self, do_login = True):
	if self.connected:
	    return True

	self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
	    self.serversocket.connect((self.server_address, self.server_port))
        except socket.error, (value,message): 
    	    if self.serversocket: 
    		self.serversocket.close() 
    	    log("e", "Could not connect to server (%s:%s): " %(self.server_address, self.server_port) + message )
	    self.connected = False
	    return False
	try:
	    kf = open(conf.c['server_public_rsa'])
	    self.server_public_key = kf.read()
	    kf.close()
	    kf = open(conf.c['client_public_rsa'])
	    self.my_public_key = kf.read()
	    kf.close()
	    kf = open(conf.c['client_private_rsa'])
	    self.my_private_key = kf.read()
	    kf.close()
	except Exception as e:
	    log("w", "Error loading key files: " + str(e) )

	self.connected = True
	# Don't wait more than 15 seconds for the server.
	self.serversocket.settimeout(conf.c['timeout'])
	log("i", "Server connection successful.")
	if do_login:
	    self.logged_in = self.login()
	else:
	    self.logged_in = False
	self.connected = True
	return True

    def disconnect(self):
	if not self.connected:
	    return True
	if self.serversocket:
	    log("w", "Closing connection to the server.")
	    try:
		#no need to authenticate when closing...
		self.send_fixed("x")
	    except:
		pass
	    self.serversocket.close()
	    self.connected = False

    def send_fixed(self, data):
	if not self.connected:
	    raise Exception("Server not connected.")

	try:
	    sent = self.serversocket.send(data)
	except socket.error, (value,message): 
	    if self.serversocket: 
    		self.serversocket.close() 
    	    raise Exception("Could not send data to server (%s:%s): " %(self.server_address, self.server_port) + message)
	    return False
	return True

    def send_dyn(self, data):
	if not self.connected:
	    raise Exception("Server not connected.")

	self.send_fixed(str(len(data)).zfill(10))
	self.send_fixed(data)
    
    def receive_fixed(self, message_len):
	if not self.connected:
	    raise Exception("Server not connected.")

	chunks = []
        bytes_recd = 0
        while bytes_recd < message_len:
            chunk = self.serversocket.recv(min(message_len - bytes_recd, 2048))
            if chunk == '':
                raise Exception("Socket connection broken (%s:%s): " %(self.server_address, self.server_port))
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)
    
    def receive_dyn(self):
	msg_size = self.receive_fixed(10)
	msg = self.receive_fixed(int(msg_size))
	return msg

    def receive_crypt(self, decryption_key, show_progress=True):
	crypt = RSACrypt()

	crypt.import_public_key(decryption_key)

	chunk_count = int(self.receive_dyn())
	received_digest = self.receive_dyn()

	org = chunk_count
	chunk_size = 256
	decrypted_results = ""
	
	if show_progress:
	    print bcolors.OKGREEN + "Progress: "
	while chunk_count > 0:
	    encrypted_chunk = self.receive_dyn()
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

    def send_crypt(self, data, encryption_key):
	crypt = RSACrypt()
	crypt.import_public_key(encryption_key)

	chunk_size = 256
	chunk_count = int(math.ceil(len(data) / float(chunk_size)))
	digest = MD5.new(data).digest()

	self.send_dyn(str(chunk_count))
	self.send_dyn(digest)
	
	ch = 0
	bytes_encrypted = 0
	encrypted_data = ""
	while bytes_encrypted < len(data):
	    ch = ch + 1
	    encrypted_chunk = crypt.public_key_encrypt(data[bytes_encrypted:min(bytes_encrypted+chunk_size, len(data))])
	    bytes_encrypted = bytes_encrypted + chunk_size
	    self.send_dyn(encrypted_chunk[0])

    def sync_results(self):
	successful = 0
	total = 0
	if not os.path.exists(conf.c['results_archive_dir']):
    	    log("i", "Creating results directory in %s" % (conf.c['results_archive_dir']))
    	    os.makedirs(conf.c['results_archive_dir'])

	for result_name in listdir(conf.c['results_dir']):
	    if isfile(join(conf.c['results_dir'],result_name)):
		log("i", "Submitting \"" + result_name + "\"...")
		total = total + 1
		if self.submit_results(result_name, join(conf.c['results_dir'],result_name)):
		    try:
			shutil.move(os.path.join(conf.c['results_dir'], result_name), os.path.join(conf.c['results_archive_dir'], result_name))
			log("i", "Moved \"" + result_name + "\" to the archive.")
		    except:
			log("e", "There was an error while moving \"" + result_name + "\" to the archive. This will be re-sent the next time.")
		    successful = successful + 1
		else:
		    log("e", "There was an error while sending \"" + result_name + "\". Will retry later.")

	log("i", "Sync complete (%d/%d were successful)." %(successful, total))

    def login(self):
	try:
	    self.send_dyn(conf.c['client_tag'])
	    if conf.c['client_tag'] <> "unauthorized":
		received_token = self.receive_crypt(self.my_private_key, show_progress=False)
		self.send_crypt(received_token, self.server_public_key)
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    log("e", "Can't log in: "), sys.exc_info()[0] 
	    return False
	
	if server_response == "a":
	    log("s", "Authentication successful.")
	elif server_response == "e":
	    raise Exception("Authentication error (could not receive error details from the server).")
	else:
	    raise Exception("Unknown server response \"" + server_response + "\"")
	return True


    def submit_results(self, name, results_file_path):
	if not self.connected:
	    raise Exception("Server not connected.")

	if conf.c['client_tag'] == 'unauthorized':
	    raise Exception("Client not authorized to send results.")

	if not self.logged_in:
	    raise Exception("Client not logged in.")

	try:
	    self.send_fixed("r")
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    raise Exception("Can't submit results: " + str(e))
	    return False

	if server_response == "a":
	    log("s", "Server ack received.")
	elif server_response == "e":
	    raise Exception("Server error.")
	    return False
	else:
	    raise Exception("Unknown server response \"" + server_response + "\"")

	try:
	    try:
		data_file = open(results_file_path, 'r')
	    except Exception as e:
		raise Exception("Can not open results file \"%s\": " %(results_file_path) + str(e))
	    
	    self.send_dyn(name)
	    data = data_file.read()
	    self.send_crypt(data, self.server_public_key)

	    server_response = self.receive_fixed(1)
	    if server_response <> "a":
		raise Exception("Success message not received.")
	except Exception as e:
	    raise Exception("Error sending data to server: " + str(e))

	return True

    def initialize_client(self):
	try:
	    self.send_dyn("unauthorized")
	    self.receive_fixed(1)
	    self.send_fixed("i")
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    raise Exception("Can\'t initialize: " + str(e))

	if server_response == "a":
	    log("s", "Server ack received.")
	elif server_response == "e":
	    raise Exception("Server error (could not receive error details from the server).")
	else:
	    raise Exception("Unknown server response \"" + server_response + "\"")

	try:
	    new_identity = self.receive_dyn() #identities are usually of length 5
	    crypt = RSACrypt()
	    my_public_key = crypt.public_key_string()
	    self.server_public_key = self.receive_dyn()
	    self.send_crypt(my_public_key, self.server_public_key)

	    server_response = self.receive_fixed(1)

	    pkf = open(conf.c['client_public_rsa'], "w")
	    pkf.write(crypt.public_key_string())
	    pkf.close()

	    pkf = open(conf.c['client_private_rsa'], "w")
	    pkf.write(crypt.private_key_string())
	    pkf.close()

	    pkf = open(conf.c['server_public_rsa'], "w")
	    pkf.write(self.server_public_key)
	    pkf.close()

	    pkf = open(conf.c['config_file'], "w")
	    pkf.write("[CentinelClient]\n")
	    pkf.write("client_tag="+new_identity)
	    pkf.close()

	    conf.c['client_tag'] = new_identity
	    if server_response == "c":
		log("s", "Server key negotiation and handshake successful. New tag: " + new_identity)
	    elif server_response == "e":
		raise Exception("Server error.")
	    else:
		raise Exception("Unknown server response \"" + server_response + "\"")
	except Exception as e:
	    raise Exception("Initialization error: " + str(e))
	
    def beat(self):
	if not self.connected:
	    raise Exception("Server not connected.")

	if conf.c['client_tag'] == 'unauthorized':
	    raise Exception("Client not authorized to send heartbeat.")

	try:
	    self.send_fixed('b')
	    server_response = self.receive_fixed(1)
	    
	    if server_response == 'b':
		return "beat"
	    elif server_response == 'c':
		return self.receive_crypt(self.my_private_key)
	    else:
		raise Exception("Server response not recognized.")
	except Exception as e:
	    raise Exception("Heartbeat error: " + str(e))
    
    def sync_experiments(self):
	if not self.connected:
	    raise Exception("Server not connected.")

	if conf.c['client_tag'] == 'unauthorized':
	    raise Exception("Client not authorized to send results.")

	self.send_fixed("s")
	
	try:
	    cur_exp_list = [os.path.basename(path) for path in glob.glob(os.path.join(conf.c['remote_experiments_dir'], '*.py'))]
	    cur_exp_list += [os.path.basename(path) for path in glob.glob(os.path.join(conf.c['remote_experiments_dir'], '*.cfg'))]

	    msg = ""
	    changed = False
	    for exp in cur_exp_list:
		exp_data = open(os.path.join(conf.c['remote_experiments_dir'], exp), 'r').read()
		msg = msg + exp + "%" + MD5.new(exp_data).digest() + "|"
	
	    if msg:
		self.send_crypt(msg[:-1], self.server_public_key)
	    else:
		self.send_crypt("n", self.server_public_key)
	    new_exp_count = self.receive_dyn()
	
	    i = int(new_exp_count)

	    if i <> 0:
		changed = True
		log("i", "%d new experiments." %(i))
		log("i", "Updating experiments...")
		while i > 0:
		    try:
			exp_name = self.receive_dyn()
			exp_content = self.receive_crypt(self.my_private_key)
			f = open(os.path.join(conf.c['remote_experiments_dir'], exp_name), "w")
			f.write(exp_content)
			f.close()
			i = i - 1
			log("s", "\"%s\" received (%d/%d)." %(exp_name, int(new_exp_count) - i, int(new_exp_count)))
		    except Exception as e:
			log("e", "Error downloading \"%s\" (%d/%d): " %(exp_name, int(new_exp_count) - i, int(new_exp_count)) + str(e))
	except Exception as e:
	    raise Exception("Error downloading new experiments: " + str(e))

	try:
    	    old_list = self.receive_crypt(self.my_private_key, False)

	    if old_list <> "n":
		changed = True
		log("i", "Removing old experiments...")
		for exp in old_list.split("|"):
		    try:
			if exp:
			    os.remove(os.path.join(conf.c['remote_experiments_dir'], exp))
			    log("i", "Removed %s." %(exp))
		    except Exception as e:
			log("e", "Error removing %s." %(exp))

	except Exception as e:
	    raise Exception("Error removing old experiments: " + str(e))

	if changed:
	    log("s", "Experiments updated.")
	return True