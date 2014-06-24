import os
import shutil
from os import listdir
from os.path import exists,isfile, join
import socket
import sys
from utils.rsacrypt import RSACrypt
from utils.colors import bcolors
from config import conf
from Crypto.Hash import MD5

conf = conf()

class ServerConnection:
    
    def __init__(self, server_address = conf.c['server_address'], server_port = int(conf.c['server_port'])):

        self.serversocket = socket.socket(
	socket.AF_INET, socket.SOCK_STREAM)
	self.server_address = server_address
	self.server_port = server_port

    def connect(self):
	try:
	    self.serversocket.connect((self.server_address, self.server_port))
        except socket.error, (value,message): 
    	    if self.serversocket: 
    		self.serversocket.close() 
    	    print bcolors.FAIL + "Could not connect to server (%s:%s): " %(self.server_address, self.server_port) + message  + bcolors.ENDC
	    self.connected = False
	    return False

	# Don't wait more than 15 seconds for the server.
	self.serversocket.settimeout(15)
	print bcolors.OKBLUE + "Server connection successful." + bcolors.ENDC
	self.connected = True
	return True

    def disconnect(self):
	if self.serversocket:
	    print bcolors.WARNING + "Closing connection to the server." + bcolors.ENDC
	    try:
		self.send_dyn(conf.c['client_tag'])
		self.send_fixed("x")
	    except:
		pass
	    self.serversocket.close()

    def submit_results(self, name, results_file_path):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    return False
	try:
	    self.send_dyn(conf.c['client_tag'])
	    server_response = self.receive_fixed(1)
	except Exception:
	    print bcolors.FAIL + "Can't submit results." + bcolors.ENDC
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
	    self.send_crypt(data_file.read())
	    server_response = self.receive_fixed(1)
	except Exception:
	    print bcolors.FAIL + "Error sending data to server." + bcolors.ENDC
	    return False

	if server_response == "e":
		try:
		    error_message = self.receive_dyn()
		    print bcolors.FAIL + "Error sending data to server: " + error_message + bcolors.ENDC
		except:
		    print bcolors.FAIL + "Server error (could not receive error details from the server)." + bcolors.ENDC
		return False
	elif server_response == "c":
	    print bcolors.OKGREEN + "Data successfully sent." + bcolors.ENDC
	    return True
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False

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
        return ''.join(chunks)
    
    def receive_dyn(self):
	msg_size = self.receive_fixed(10)
	msg = self.receive_fixed(int(msg_size))
	return msg


    def send_crypt(self, data):
	print bcolors.OKBLUE + "Awaiting server key..." + bcolors.ENDC
	server_public_key = self.receive_dyn()
	print bcolors.OKGREEN + "Server key received." + bcolors.ENDC

	
	crypt = RSACrypt()
	crypt.import_public_key(server_public_key)

	chunk_size = 256
	chunk_count = int(len(data) / chunk_size) + 1
	digest = MD5.new(data).digest()

	print bcolors.OKBLUE + "Sending %d chunks of encrypted data..." %(chunk_count) + bcolors.ENDC

	self.send_dyn(str(chunk_count))
	self.send_dyn(digest)
	
	bytes_encrypted = 0
	while bytes_encrypted < len(data):
	    enc_data = crypt.public_key_encrypt(data[bytes_encrypted:min(bytes_encrypted+chunk_size, len(data))])
	    bytes_encrypted = bytes_encrypted + chunk_size
	    self.send_dyn(enc_data[0])
	print bcolors.OKGREEN + "Encrypted data sent." + bcolors.ENDC

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
