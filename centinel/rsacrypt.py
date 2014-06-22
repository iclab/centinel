from Crypto.PublicKey import RSA
from Crypto import Random

class RSACrypt:
    
    def __init__(self):
	random_generator = Random.new().read
	self.key = RSA.generate(2048, random_generator)
	self.public_key = self.key.publickey()
	#print "Key generated, maximum number of bytes that it can handle is: " + str(self.public_key.size())
    
    def public_key_encrypt(self, data):
	enc_data = self.public_key.encrypt(data, 8192)
	return enc_data

    def private_key_decrypt(self, enc_data):
	data = self.key.decrypt(enc_data)
	return data

    def public_key_decrypt(self, enc_data):
	return self.public_key.decrypt(enc_data)

    def public_key_string(self):
	return self.public_key.exportKey('PEM')
    
    def import_public_key(self,new_public_key):
	self.public_key = RSA.importKey(new_public_key)

    def size_cap(self):
	return self.public_key.size()