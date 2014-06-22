import socket
import sys
import threading
from datetime import datetime
from rsacrypt import RSACrypt
from Crypto.Hash import MD5

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class Server:
    def __init__(self, sock=None):
	if sock is None:
	    #create an INET, STREAMing socket
    	    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	else:
	    self.sock = sock
	self.sock.bind(('', 8082))
	self.sock.listen(5)

    def send_fixed(self, clientsocket, address, data):
	try:
	    sent = clientsocket.send(data)
	except socket.error, (value,message): 
	    if clientsocket: 
    		clientsocket.close() 
    	    print bcolors.FAIL + "Could not send data to client (%s:%s): " %(address[0], address[1]) + message  + bcolors.ENDC
	    return False
	    
	#print "Sent %d bytes to the client." %(sent)
	return True
    
    def send_dyn(self, clientsocket, address, data):
	self.send_fixed(clientsocket, address, str(len(data)).zfill(10))
	self.send_fixed(clientsocket, address, data)
    
    def receive_fixed(self, clientsocket, address, message_len):
	chunks = []
        bytes_recd = 0
        while bytes_recd < message_len:
            chunk = clientsocket.recv(min(message_len - bytes_recd, 2048))
            if chunk == '':
                print bcolors.FAIL + "Socket connection broken (%s:%s)" %(address[0], address[1]) + bcolors.ENDC
        	return False
	    chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)
    
    def receive_dyn(self, clientsocket, address):
	msg_size = self.receive_fixed(clientsocket, address, 10)
	msg = self.receive_fixed(clientsocket, address, int(msg_size))
	return msg

    def receive_crypt(self, clientsocket, address):
	crypt = RSACrypt()
	print bcolors.OKBLUE + "Sending RSA key..." + bcolors.ENDC

	self.send_dyn(clientsocket, address, crypt.public_key_string())
	chunk_count = int(self.receive_dyn(clientsocket, address))
	received_digest = self.receive_dyn(clientsocket, address)

	print bcolors.OKBLUE + "Receiving %d chunks of encrypted data..." %(chunk_count) + bcolors.ENDC
	results_decrypted = ""
	while chunk_count > 0:
	    encrypted_chunk = self.receive_dyn(clientsocket, address)
	    results_decrypted = results_decrypted + crypt.private_key_decrypt(encrypted_chunk)
	    chunk_count = chunk_count - 1
	
	print bcolors.OKGREEN + "Encrypted data received." + bcolors.ENDC
	print bcolors.OKBLUE + "Verifying data integrity..." + bcolors.ENDC

	calculated_digest = MD5.new(results_decrypted).digest()
	if calculated_digest == received_digest:
	    print bcolors.OKGREEN + "Data integrity check pass." + bcolors.ENDC
	    return results_decrypted
	else:
	    print bcolors.FAIL + "Data integrity check failed." + bcolors.ENDC
	    return False

    def run(self):
	print bcolors.HEADER + "Server running. Awaiting connections..." + bcolors.ENDC
	while 1:
	    #accept connections from outside
	    (clientsocket, address) = self.sock.accept()
	    print bcolors.OKBLUE + "Got a connection from " + address[0] + bcolors.ENDC
	    client_thread = threading.Thread(target=self.client_connection_handler, args = (clientsocket, address))
	    client_thread.daemon = True
	    client_thread.start()

    def client_connection_handler(self, clientsocket, address):
	# r: results
	# l: test_list
	message_type = self.receive_fixed(clientsocket, address, 1)
	
	# The client wants to submit results:
	if message_type == "r":
	    print bcolors.OKGREEN + address[0] + ":" + str(address[1]) + " wants to submit results." + bcolors.ENDC
	    try:
    		self.send_fixed(clientsocket, address, "a")
		results_name = self.receive_dyn(clientsocket, address)

		results_decrypted = self.receive_crypt(clientsocket, address)

		out_file = open(datetime.now().time().isoformat() + "-" + results_name, 'w')
		out_file.write(results_decrypted)
		out_file.close()
	    except socket.error, (value,message): 
		if clientsocket: 
    		    clientsocket.close() 
    		print bcolors.FAIL + address[0] + ":" + str(address[1]) + " error receiving data: " + message  + bcolors.ENDC
		self.send_fixed(clientsocket, address, "e")
		self.send_dyn(clientsocket, address, message)
		return False
	
	    print bcolors.OKGREEN + address[0] + ":" + str(address[1]) + " results recorded." + bcolors.ENDC
	    self.send_fixed(clientsocket, address, "c")
	    if clientsocket: 
    	        clientsocket.close() 
	    return True

	self.send_fixed(clientsocket, address, "e")
	self.send_dyn(clientsocket, address, "Message type not recognized.")

    	if clientsocket: 
    	    clientsocket.close() 

	return False
s = Server()
s.run()