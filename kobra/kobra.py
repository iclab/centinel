#! /usr/bin/python

import sys
sys.path.append("../")

import threading
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
import socket
from utils.rsacrypt import RSACrypt
from utils.aescrypt import AESCipher
from utils.colors import bcolors
from utils.colors import update_progress
from utils.logger import *
from Crypto.Hash import MD5
from getpass import getpass

class KobraConnection:
    
    def __init__(self, server_addresses, server_port):
	self.server_addresses = server_addresses.split(" ")
	self.server_address = ""
	self.server_port = server_port
	self.connected = False
	self.aes_secret = ""
	self.username = ""
	self.end_session = False
	
    def connect(self):
	if self.connected:
	    return True

	self.connected = False
	for address in self.server_addresses:
	    try:
		self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

	# Don't wait more than 15 seconds for the server.
	self.serversocket.settimeout(15)
	log("i", "Server connection successful.")
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

    def login(self, username, password):
	try:
	    log("i", "Authenticating with the server...")
	    self.send_dyn(username)
	    received_token = self.receive_aes_crypt(password, show_progress=False)
	    self.send_aes_crypt(received_token, password)
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
	
	self.username = username
	self.aes_secret = received_token
	return True

    def run(self):
	try:
	    while True:
		try:
    		    command = raw_input(self.username + "@" + self.server_address + "# ")
		    self.send_aes_crypt(command, self.aes_secret)
		except Exception as e:
		    log("e", "Error sending message to the server: " + str(e))
		    return
		try:
		    server_message = self.receive_aes_crypt(self.aes_secret, show_progress=False)
		except socket.timeout:
		    pass
		except Exception as e:
		    log("e", "Error receiving server message: " + str(e))
		    return

		if server_message == "<END>":
		    print "Server wants to end connection"
		    return
		if server_message == "<FILE>":
	    	    print "Server wants to send a file, where shall we save it?"
	    	    # TODO:
	    	    # implement.

		if server_message == "<START_MESSAGE>":
		    while server_message != "<END_MESSAGE>":
			server_message = self.receive_aes_crypt(self.aes_secret, show_progress=False)
			if server_message != "<END_MESSAGE>":
			    print server_message

	except (KeyboardInterrupt, SystemExit):
	    log("w", "Shutdown requested, shutting Kobra down...")
	    # do some shutdown stuff, then close
	    self.serversocket.close()
	    self.end_session = True
	    return

	return


username = ""
password = ""
server = "nrgairport.nrg.cs.stonybrook.edu 130.245.145.2"
port = "8083"

if len(sys.argv) == 2:
    if len(sys.argv[1].split("@")) == 2:
	username = sys.argv[1].split("@")[0]
	server = sys.argv[1].split("@")[1]
    else:
	server = sys.argv[1]

if len(server.split(":")) == 2:
    server = server.split(":")[0]
    port = server.split(":")[1]

if not server:
    server = raw_input("Enter server address: ")
    while not server:
	server = raw_input ("Server address cannot be empty, enter again: ")

if not port:
    port = raw_input("Enter server port: ")
    while not port:
	port = raw_input ("Server port cannot be empty, enter again: ")

if not username:
    username = raw_input("Enter username: ")
    while not username:
	username = raw_input ("Username cannot be empty, enter again: ")

if not password:
    password = getpass("Enter password: ")
    while not password:
	password = getpass ("Password cannot be empty, enter again: ")


logging.basicConfig(filename="/tmp/kobra.log", level=logging.DEBUG)

kobraconn = KobraConnection(server, int(port))
kobraconn.connect()
if kobraconn.login(username, password) == True:
    kobraconn.run()
else:
    print "Error logging in!"