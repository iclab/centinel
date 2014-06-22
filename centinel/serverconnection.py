import socket
import sys
from rsacrypt import RSACrypt
from Crypto.Hash import MD5

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class ServerConnection:
    
    def __init__(self, server_address, server_port):

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
	print bcolors.OKBLUE + "Server connection successful." + bcolors.ENDC
	self.connected = True
	return True

    def disconnect(self):
	print bcolors.WARNING + "Closing connection to the server." + bcolors.ENDC
	if self.serversocket:
	    self.serversocket.close()

    def submit_results(self, name, results_file_path):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    return False
	self.send_fixed("r")
	server_response = self.receive_fixed(1)
	
	if server_response == "a":
	    print bcolors.OKGREEN + "Server ack received." + bcolors.ENDC
	elif server_response == "e":
	    error_message = self.receive_dyn()
	    print bcolors.FAIL + "Server error: " + error_message + bcolors.ENDC
	    return False
	else:
	    print bcolors.FAIL + "Unknown server response \"" + server_response + "\"" + bcolors.ENDC
	    return False


	data_file = open(results_file_path, 'r')
	self.send_dyn(name)
	self.send_crypt(data_file.read())

	server_response = self.receive_fixed(1)
	
	if server_response == "e":
	    error_message = self.receive_dyn()
	    print bcolors.FAIL + "Error sending data: " + error_message + bcolors.ENDC
	    return False

	if server_response == "c":
	    print bcolors.OKGREEN + "Data successfully sent." + bcolors.ENDC
	    return True

    def send_fixed(self, data):
	try:
	    sent = self.serversocket.send(data)
	except socket.error, (value,message): 
	    if self.serversocket: 
    		self.serversocket.close() 
    	    print "Could not send data to server (%s:%s): " %(self.server_address, self.server_port) + message  + bcolors.ENDC
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
	    return False
	chunks = []
        bytes_recd = 0
        while bytes_recd < message_len:
            chunk = self.serversocket.recv(min(message_len - bytes_recd, 2048))
            if chunk == '':
                raise RuntimeError("Socket connection broken")
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)
    
    def receive_dyn(self):
	if not self.connected:
	    print bcolors.FAIL + "Server not connected!" + bcolors.ENDC
	    return False
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

	