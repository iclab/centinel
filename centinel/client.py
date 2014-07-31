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
from datetime import datetime, timedelta
from os.path import exists,isfile, join
import socket, ssl, pprint
import M2Crypto

from utils.rsacrypt import RSACrypt
from utils.aescrypt import AESCipher
from utils.colors import bcolors
from utils.colors import update_progress
from utils.logger import *
from client_config import client_conf
from Crypto.Hash import MD5

conf = client_conf()

class ServerConnection:
    
    def __init__(self, server_addresses = conf.c['server_addresses'], server_port = int(conf.c['server_port'])):
	self.server_addresses = server_addresses.split(" ")
	self.server_address = ""
	self.server_port = server_port
	self.connected = False
	self.aes_secret = ""
	
    def connect(self, do_login = True):
	if self.connected:
	    return True

	self.connected = False
	for address in self.server_addresses:
	    try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		self.serversocket = ssl.wrap_socket(s,
                    				    #ca_certs="/etc/ssl/certs/ca-certificates.crt",
                        			    #cert_reqs=ssl.CERT_REQUIRED,
						    ssl_version=ssl.PROTOCOL_TLSv1
    						   )

		self.serversocket.connect((address, self.server_port))

		
		self.connected = True
		self.server_address = address
		break
    	    except socket.error, (value,message): 
    		if self.serversocket: 
    		    self.serversocket.close() 
    		log("e", "Could not connect to server (%s:%s): " %(address, self.server_port) + message )
		self.connected = False
	if not self.connected:
	    return False
	else:
	    log("s", "Connected to %s:%s." %(self.server_address, self.server_port) )
		
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
	self.serversocket.settimeout(int(conf.c['timeout']))
	log("i", "Server connection successful.")
	if do_login:
	    try:
		self.logged_in = self.login()
	    except Exception as e:
		log("e", "Error logging in: " + str(e))
		self.logged_in = False
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

    """
    Send a string of characters encrpyted using a given AES key.
	The message will be chopped up into chunks of fixed size.
	The number of encrypted chunks is sent, followed by the
	hash of the unencrypted data (used for integrity checking).
	Encrypted chunks are sent one by one after that.
    """
    def send_aes_crypt(self, data, encryption_key):
	crypt = AESCipher(encryption_key)

	chunk_size = 1024
	chunk_count = int(math.ceil(len(data) / float(chunk_size)))
	digest = MD5.new(data).digest()

	self.send_dyn(str(chunk_count))
	self.send_dyn(digest)
	
	bytes_encrypted = 0
	encrypted_data = ""
	while bytes_encrypted < len(data):
	    encrypted_chunk = crypt.encrypt(data[bytes_encrypted:min(bytes_encrypted+chunk_size, len(data))])
	    bytes_encrypted = bytes_encrypted + chunk_size
	    self.send_dyn(encrypted_chunk)

    """
    Receive a string of characters encrpyted using a given AES key.
	The message will be received in chunks of fixed size.
	The number of encrypted chunks is received, followed by the
	hash of the unencrypted data (used for integrity checking).
	Encrypted chunks are received one by one after that and 
	decrypted using the given key. The resulting string is then
	hashed and verified using the received hash.
    """
    def receive_aes_crypt(self, decryption_key, show_progress=True):
	crypt = AESCipher(decryption_key)

	chunk_count = int(self.receive_dyn())
	received_digest = self.receive_dyn()

	org = chunk_count
	chunk_size = 1024
	decrypted_results = ""
	byte_rate = ""
	start_time = datetime.now()
	if show_progress and chunk_count:
	    print bcolors.OKBLUE + "Progress: "
	while chunk_count > 0:
	    encrypted_chunk = self.receive_dyn()
	    decrypted_results = decrypted_results + crypt.decrypt(encrypted_chunk)
	    chunk_count = chunk_count - 1
	    if show_progress:
		time_elapsed = (datetime.now() - start_time).seconds
		if  time_elapsed > 0:
		    byte_rate = str((float(len(decrypted_results)) / float(time_elapsed)) / 1024.0)
		update_progress( int(100 * float(org - chunk_count) / float(org)), byte_rate + " Kb/s " if byte_rate else "" )
	if show_progress:
	    print bcolors.ENDC

	calculated_digest = MD5.new(decrypted_results).digest()
	if calculated_digest == received_digest:
	    return decrypted_results
	else:
	    raise Exception("AES: data integrity check failed.")
	    return False

    def receive_rsa_crypt(self, decryption_key, show_progress=True):
	crypt = RSACrypt()

	crypt.import_public_key(decryption_key)

	chunk_count = int(self.receive_dyn())
	received_digest = self.receive_dyn()

	org = chunk_count
	chunk_size = 256
	decrypted_results = ""
	byte_rate = ""
	start_time = datetime.now()
	if show_progress:
	    print bcolors.OKGREEN + "Progress: "
	while chunk_count > 0:
	    encrypted_chunk = self.receive_dyn()
	    decrypted_results = decrypted_results + crypt.public_key_decrypt(encrypted_chunk)
	    chunk_count = chunk_count - 1
	    if show_progress:
		time_elapsed = (datetime.now() - start_time).seconds
		if  time_elapsed > 0:
		    byte_rate = str((float(len(decrypted_results)) / float(time_elapsed)) / 1024.0)
		update_progress( int(100 * float(org - chunk_count) / float(org)), byte_rate + " Kb/s " if byte_rate else "" )
	if show_progress:
	    print bcolors.ENDC
    
	calculated_digest = MD5.new(decrypted_results).digest()
	if calculated_digest == received_digest:
	    return decrypted_results
	else:
	    raise Exception("RSA: data integrity check failed.")

    def send_rsa_crypt(self, data, encryption_key):
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

    def login(self):

	try:
	    received_server_cert = ssl.DER_cert_to_PEM_cert(self.serversocket.getpeercert(True))
	
	    if received_server_cert != open(conf["server_certificate"], "r").read():
		raise Exception("Server certificate can not be recognized!")
	    x509 = M2Crypto.X509.load_cert_string(received_server_cert)
	    
	    log("w", "Server certificate details: " + pprint.pformat(x509.get_subject().as_text()))
	except Exception as e:
	    raise Exception("Error verifying server certificate: " + str(e))

	try:
	    log("i", "Authenticating with the server...")
	    self.send_dyn(conf.c['client_tag'])
	    if conf.c['client_tag'] <> "unauthorized":
		received_token = self.receive_rsa_crypt(self.my_private_key, show_progress=False)
		self.send_rsa_crypt(received_token, self.server_public_key)
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    log("e", "Can't authenticate: " + str(e)) 
	    return False
	
	if server_response == "a":
	    log("s", "Authentication successful.")
	elif server_response == "e":
	    raise Exception("Authentication error (could not receive error details from the server).")
	else:
	    raise Exception("Unknown server response \"" + server_response + "\"")

	self.aes_secret = received_token
	return True

    def check_for_updates(self):
	try:
	    client_version = open(".version", "r").read()
	    self.send_fixed("v")
	    self.send_aes_crypt(client_version, self.aes_secret)
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    raise Exception("Error checking for updates: " + str(e))

	if server_response == "u":
	    log("w", "There is a newer version of Centinel available.")
	    log("i", "Downloading update package...")
	    try:
	        update_package_contents = self.receive_aes_crypt(self.aes_secret, show_progress=True)
		of = open("update.tar.bz2", "w")
		of.write(update_package_contents)
		of.close()
	    except Exception as e:
	        raise Exception("Error downloading update package: " + str(e))
	    return True
	elif server_response == "a":
	    return False
	else:
	    raise Exception("Error checking for updates: server response not recognized!")
		

    def send_file(self, name, file_path, message):
	if not self.connected:
	    raise Exception("Server not connected.")

	if conf.c['client_tag'] == 'unauthorized':
	    raise Exception("Client not authorized to send files.")

	if not self.logged_in:
	    raise Exception("Client not logged in.")

	try:
	    self.send_fixed(message)
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    raise Exception("Can't submit file: " + str(e))
	    return False

	if server_response == "a":
	    #log("s", "Server ack received.")
	    pass
	elif server_response == "e":
	    raise Exception("Server error.")
	    return False
	else:
	    raise Exception("Unknown server response \"" + server_response + "\"")

	try:
	    try:
		data_file = open(file_path, 'r')
	    except Exception as e:
		raise Exception("Can not open file \"%s\": " %(file_path) + str(e))
	    
	    data = data_file.read()
	    self.send_aes_crypt(name, self.aes_secret)
	    self.send_aes_crypt(data, self.aes_secret)

	    server_response = self.receive_fixed(1)
	    if server_response <> "a":
		raise Exception("Success message not received.")
	except Exception as e:
	    raise Exception("Error sending file to server: " + str(e))

	return True

    def initialize_client(self):
	
	try:
	    received_server_cert = ssl.DER_cert_to_PEM_cert(self.serversocket.getpeercert(True))
	
	    x509 = M2Crypto.X509.load_cert_string(received_server_cert)
	    log("w", "Server certificate details: " + pprint.pformat(x509.get_subject().as_text()))

	    of = open(conf["server_certificate"], "w")
	    of.write(received_server_cert)
	    of.close()
	except Exception as e:
	    raise Exception("Can not write server certificate: " + str(e))

	try:

	    self.send_dyn("unauthorized")
	    self.receive_fixed(1)
	    self.send_fixed("i")
	    server_response = self.receive_fixed(1)
	except Exception as e:
	    raise Exception("Can\'t initialize: " + str(e))

	if server_response == "a":
	    #log("s", "Server ack received.")
	    pass
	elif server_response == "e":
	    raise Exception("Server error (could not receive error details from the server).")
	else:
	    raise Exception("Unknown server response \"" + server_response + "\"")

	try:
	    crypt = RSACrypt()
	    my_public_key = crypt.public_key_string()
	    self.server_public_key = self.receive_dyn()
	    self.send_rsa_crypt(my_public_key, self.server_public_key)
	    new_identity = self.receive_rsa_crypt(crypt.private_key_string()) #identities are usually of length 5

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


	    conf.c['client_tag'] = new_identity
	    if server_response == "c":
		log("s", "Server key negotiation and handshake successful. New tag: " + new_identity)
		conf.set("client_tag",new_identity)
		conf.update()

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
		return self.receive_aes_crypt(self.aes_secret, show_progress=False)
	    else:
		raise Exception("Server response not recognized.")
	except Exception as e:
	    raise Exception("Heartbeat error: " + str(e))

    def send_logs(self):
	successful = 0
	total = 0
	if not os.path.exists(conf.c['logs_dir']):
    	    log("i", "Creating logs directory in %s" % (conf.c['logs_dir']))
    	    os.makedirs(conf.c['results_archive_dir'])

	for log_name in listdir(conf.c['logs_dir']):
	    if isfile(join(conf.c['logs_dir'],log_name)):
		log("i", "Sending \"" + log_name + "\"...")
		total = total + 1
		try:
		    self.send_file(log_name, join(conf.c['logs_dir'], log_name), "g")
		    log("s", "Sent \"" + log_name + "\" to the server.")
		    os.remove(os.path.join(conf.c['logs_dir'], log_name))
		    successful = successful + 1
		except Exception as e:
		    log("e", "There was an error while sending \"" + log_name + "\": %s. Will retry later." %(str(e)))

	if total:
	    log("s", "Sending logs complete (%d/%d were successful)." %(successful, total))
	else:
	    log("i", "Sending logs complete (nothing sent).")

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
		try:
		    self.send_file(result_name, join(conf.c['results_dir'], result_name), "r")
		    try:
			shutil.move(os.path.join(conf.c['results_dir'], result_name), os.path.join(conf.c['results_archive_dir'], result_name))
			log("s", "Moved \"" + result_name + "\" to the archive.")
		    except:
			log("e", "There was an error while moving \"" + result_name + "\" to the archive. This will be re-sent the next time.")
		    successful = successful + 1
		except Exception as e:
		    log("e", "There was an error while sending \"" + result_name + "\": %s. Will retry later." %(str(e)))
	if total:
	    log("s", "Sync complete (%d/%d were successful)." %(successful, total))
	else:
	    log("i", "Sync complete (nothing sent).")


    def sync_experiments(self):
	if not self.connected:
	    raise Exception("Server not connected.")

	if conf.c['client_tag'] == 'unauthorized':
	    raise Exception("Client not authorized to sync experiments.")

	self.send_fixed("s")
	
	try:
	    cur_exp_list = [os.path.basename(path) for path in glob.glob(os.path.join(conf.c['remote_experiments_dir'], '*.py'))]
	    cur_exp_list += [os.path.basename(path) for path in glob.glob(os.path.join(conf.c['remote_experiments_dir'], '*.cfg'))]

	    msg = ""
	    changed = False
	    for exp in cur_exp_list:
		exp_content = open(os.path.join(conf.c['remote_experiments_dir'], exp), 'r').read()
		msg = msg + exp + "%" + MD5.new(exp_content).digest() + "|"
	
	    if msg:
		self.send_aes_crypt(msg[:-1], self.aes_secret)
	    else:
		self.send_aes_crypt("n", self.aes_secret)
	    new_exp_count = self.receive_dyn()
	
	    i = int(new_exp_count)

	    if i <> 0:
		changed = True
		log("i", "%d new experiments." %(i))
		log("i", "Updating experiments...")
		while i > 0:
		    try:
			i = i - 1
			exp_name = self.receive_aes_crypt(self.aes_secret, show_progress = False)
			exp_content = self.receive_aes_crypt(self.aes_secret)
			f = open(os.path.join(conf.c['remote_experiments_dir'], exp_name), "w")
			f.write(exp_content)
			f.close()
			log("s", "\"%s\" received (%d/%d)." %(exp_name, int(new_exp_count) - i, int(new_exp_count)))
		    except Exception as e:
			try:
			    log("e", "Error downloading \"%s\" (%d/%d): " %(exp_name, int(new_exp_count) - i, int(new_exp_count)) + str(e))
			except:
			    log("e", "Error downloading experiment %d of %d." %(int(new_exp_count) - i, int(new_exp_count)) + str(e))
	except Exception as e:
	    raise Exception("Error downloading new experiments: " + str(e))

	try:
    	    old_list = self.receive_aes_crypt(self.aes_secret, False)

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
	
	try:
	    cur_exp_data_list = [os.path.basename(path) for path in glob.glob(os.path.join(conf.c['experiment_data_dir'], '*.txt'))]

	    msg = ""

	    for exp_data in cur_exp_data_list:
		exp_data_contents = open(os.path.join(conf.c['experiment_data_dir'], exp_data), 'r').read()
		msg = msg + exp_data + "%" + MD5.new(exp_data_contents).digest() + "|"
	
	    if msg:
		self.send_aes_crypt(msg[:-1], self.aes_secret)
	    else:
		self.send_aes_crypt("n", self.aes_secret)
	    new_exp_data_count = self.receive_dyn()
	
	    i = int(new_exp_data_count)

	    if i <> 0:
		changed = True
		log("i", "%d new experiment data files." %(i))
		log("i", "Updating experiment data files...")
		while i > 0:
		    try:
			exp_data_name = self.receive_aes_crypt(self.aes_secret, show_progress=False)
			exp_data_content = self.receive_aes_crypt(self.aes_secret)
			f = open(os.path.join(conf.c['experiment_data_dir'], exp_data_name), "w")
			f.write(exp_data_content)
			f.close()
			i = i - 1
			log("s", "\"%s\" received (%d/%d)." %(exp_data_name, int(new_exp_data_count) - i, int(new_exp_data_count)))
		    except Exception as e:
			log("e", "Error downloading \"%s\" (%d/%d): " %(exp_data_name, int(new_exp_data_count) - i, int(new_exp_data_count)) + str(e))
	except Exception as e:
	    raise Exception("Error downloading new experiment data files: " + str(e))

	try:
    	    old_list = self.receive_aes_crypt(self.aes_secret, False)

	    if old_list <> "n":
		changed = True
		log("i", "Removing old experiment data files...")
		for exp_data in old_list.split("|"):
		    try:
			if exp_data:
			    os.remove(os.path.join(conf.c['experiment_data_dir'], exp_data))
			    log("i", "Removed \"%s\"." %(exp_data))
		    except Exception as e:
			log("e", "Error removing \"%s\"." %(exp_data))

	except Exception as e:
	    raise Exception("Error removing old experiment data files: " + str(e))

	if changed:
	    log("s", "Experiments updated.")
	return True