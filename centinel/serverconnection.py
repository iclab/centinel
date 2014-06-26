import math
import os
import shutil
import random
import string
from os import listdir
import StringIO
import gzip
from os.path import exists,isfile, join
import socket
import sys
from utils.rsacrypt import RSACrypt
from utils.colors import bcolors
from utils.colors import update_progress
from client_config import client_conf
from Crypto.Hash import MD5

conf = client_conf()

class ServerConnection:
    
    def __init__(self, server_address = conf.c['server_address'], server_port = int(conf.c['server_port'])):
        self.serversocket = socket.socket(
	socket.AF_INET, socket.SOCK_STREAM)
	self.server_address = server_address
	self.server_port = server_port
	
    def connect(self, do_login = True):
	try:
	    self.serversocket.connect((self.server_address, self.server_port))
        except socket.error, (value,message): 
    	    if self.serversocket: 
    		self.serversocket.close() 
    	    print bcolors.FAIL + "Could not connect to server (%s:%s): " %(self.server_address, self.server_port) + message  + bcolors.ENDC
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
	except:
	    print bcolors.WARNING + "Error loading key files."  + bcolors.ENDC

	self.connected = True
	# Don't wait more than 15 seconds for the server.
	self.serversocket.settimeout(15)
	print bcolors.OKBLUE + "Server connection successful." + bcolors.ENDC
	if do_login:
	    self.logged_in = self.login()
	else:
	    self.logged_in = False
	self.connected = True
	return True

    def disconnect(self):
	if self.serversocket:
	    print bcolors.WARNING + "Closing connection to the server." + bcolors.ENDC
	    try:
		#no need to authenticate when closing...
		self.send_dyn("unauthorized")
		self.send_fixed("x")
	    except:
		pass
	    self.serversocket.close()

    def send_fixed(self, data):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    raise Exception("Not connected.")
	    return False

	try:
	    sent = self.serversocket.send(data)
	except socket.error, (value,message): 
	    if self.serversocket: 
    		self.serversocket.close() 
    	    raise Exception("Could not send data to server (%s:%s): " %(self.server_address, self.server_port) + message)
	    return False
	    
	#print "Sent %d bytes to the server." %(sent)
	return True

    def send_dyn(self, data):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    return False
	self.send_fixed(str(len(data)).zfill(10))
	self.send_fixed(data)
    
    def receive_fixed(self, message_len):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    raise Exception("Not connected.")
	    return False
	chunks = []
        bytes_recd = 0
        while bytes_recd < message_len:
            chunk = self.serversocket.recv(min(message_len - bytes_recd, 2048))
            if chunk == '':
                raise Exception("Socket connection broken (%s:%s): " %(self.server_address, self.server_port))
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
	#print ''.join(chunks)
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
	    print bcolors.OKBLUE + "Progress: "
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
	    print bcolors.FAIL + "Data integrity check failed." + bcolors.ENDC
	    return False


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
    	    print "Creating results directory in %s" % (conf.c['results_archive_dir'])
    	    os.makedirs(conf.c['results_archive_dir'])

	for result_name in listdir(conf.c['results_dir']):
	    if isfile(join(conf.c['results_dir'],result_name)):
		print bcolors.OKBLUE + "Submitting \"" + result_name + "\"..." + bcolors.ENDC
		total = total + 1
		if self.submit_results(result_name, join(conf.c['results_dir'],result_name)):
		    try:
			shutil.move(os.path.join(conf.c['results_dir'], result_name), os.path.join(conf.c['results_archive_dir'], result_name))
			print bcolors.OKBLUE + "Moved \"" + result_name + "\" to the archive." + bcolors.ENDC
		    except:
			print bcolors.FAIL + "There was an error while moving \"" + result_name + "\" to the archive. This will be re-sent the next time!" + bcolors.ENDC
		    successful = successful + 1
		else:
		    print bcolors.FAIL + "There was an error while sending \"" + result_name + "\". Will retry later." + bcolors.ENDC

	print bcolors.OKBLUE + "Sync complete (%d/%d were successful)." %(successful, total) + bcolors.ENDC

    def login(self):
	try:
	    self.send_dyn(conf.c['client_tag'])
	    if conf.c['client_tag'] <> "unauthorized":
		received_token = self.receive_crypt(self.my_private_key, show_progress=False)
		self.send_crypt(received_token, self.server_public_key)
	    server_response = self.receive_fixed(1)
	except Exception:
	    print bcolors.FAIL + "Can't log in: " + bcolors.ENDC, sys.exc_info()[0] 
	    return False
	
	if server_response == "a":
	    print bcolors.OKGREEN + "Authentication successful." + bcolors.ENDC
	elif server_response == "e":
	    try:
		error_message = self.receive_dyn()
		print bcolors.FAIL + "Authentication error: " + error_message + bcolors.ENDC
	    except Exception:
		print bcolors.FAIL + "Authentication error (could not receive error details from the server)." + bcolors.ENDC
	    return False
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False
	return True


    def submit_results(self, name, results_file_path):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    return False

	if conf.c['client_tag'] == 'unauthorized' or not self.logged_in:
	    print bcolors.FAIL + "Client not authorized to send results." + bcolors.ENDC
	    return False

	try:
	    self.send_fixed("r")
	    server_response = self.receive_fixed(1)
	except Exception:
	    print bcolors.FAIL + "Can't submit results." + bcolors.ENDC
	    return False

	if server_response == "a":
	    print bcolors.OKGREEN + "Server ack received." + bcolors.ENDC
	elif server_response == "e":
	    try:
		error_message = self.receive_dyn()
		print bcolors.FAIL + "Server error: " + error_message + bcolors.ENDC
	    except Exception:
		print bcolors.FAIL + "Server error (could not receive error details from the server)." + bcolors.ENDC
	    return False
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False

	try:
	    try:
		data_file = open(results_file_path, 'r')
	    except:
		print bcolors.FAIL + "Can not open results file!" + bcolors.ENDC
		return False
	    
	    self.send_dyn(name)
	    data = data_file.read()
	    self.send_crypt(data, self.server_public_key)

	    server_response = self.receive_fixed(1)
	except Exception:
	    print bcolors.FAIL + "Error sending data to server." + bcolors.ENDC
	    return False

	if server_response == "e":
		try:
		    error_message = self.receive_dyn()
		    print bcolors.FAIL + "Error sending data to server: " + error_message + bcolors.ENDC
		    return False
		except:
		    print bcolors.FAIL + "Server error (could not receive error details from the server)." + bcolors.ENDC
		return False
	elif server_response == "c":
	    print bcolors.OKGREEN + "Data successfully sent." + bcolors.ENDC
	    return True
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False

	return True

    def initialize_client(self):
	try:
	    self.send_dyn("unauthorized")
	    self.receive_fixed(1)
	    self.send_fixed("i")
	    server_response = self.receive_fixed(1)
	except Exception:
	    print bcolors.FAIL + "Can\'t initialize." + bcolors.ENDC
	    return False

	if server_response == "a":
	    print bcolors.OKGREEN + "Server ack received." + bcolors.ENDC
	elif server_response == "e":
	    try:
		error_message = self.receive_dyn()
		print bcolors.FAIL + "Server error: " + error_message + bcolors.ENDC
	    except Exception:
		print bcolors.FAIL + "Server error (could not receive error details from the server)." + bcolors.ENDC
	    return False
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False

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
	    print bcolors.OKGREEN + "Server key negotiation and handshake successful. New tag: " + new_identity + bcolors.ENDC
	elif server_response == "e":
	    try:
		error_message = self.receive_dyn()
		print bcolors.FAIL + "Server error: " + error_message + bcolors.ENDC
	    except Exception:
		print bcolors.FAIL + "Server error (could not receive error details from the server)." + bcolors.ENDC
	    return False
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False
	
    def beat(self):
        if not self.logged_in:
	    print bcolors.FAIL + "Unauthorized hearts don't beat! " + bcolors.ENDC
	    return False

	self.send_fixed('b')
	server_response = self.receive_fixed(1)
	    
	if server_response == 'b':
	    return "beat"
	elif server_response == 'c':
	    return self.receive_crypt(self.my_private_key)
	else:
	    return False
    
    def sync_exp(self):
	if not self.logged_in:
	    print bcolors.FAIL + "Unauthorized hearts don't beat! " + bcolors.ENDC
	    return False

	#self.send_fixed("s")
	
	#py_exp_pairs = [  MD5.new(data).digest()
