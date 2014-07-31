import zlib
import struct
import base64
from Crypto.Cipher import AES
from Crypto import Random

class CheckSumError(Exception):
    pass

class AESCipher:

    def __init__(self, key):
	self.bs = 32
	if len(key) >= 32:
    	    self.key = key[:32]
	else:
    	    self.key = self._pad(key)

    def encrypt(self, plaintext, checksum=True):
	"""encrypt plaintext with secret
	plaintext   - content to encrypt
	checksum    - attach crc32 byte encoded (default: True)
	returns ciphertext
	"""
	plaintext = self._pad(plaintext)
	iv = Random.new().read(AES.block_size)
	encobj = AES.new(self.key, AES.MODE_CFB, iv)

	if checksum:
    	    plaintext += struct.pack("i", zlib.crc32(plaintext))

	return base64.b64encode(iv + encobj.encrypt(plaintext))

    def decrypt(self, ciphertext, checksum=True):
	"""decrypt ciphertext with secret
	ciphertext  - encrypted content to decrypt
	checksum    - verify crc32 byte encoded checksum (default: True)
    	returns plaintext
	"""
	ciphertext = base64.b64decode(ciphertext)
	iv = ciphertext[:AES.block_size]

	encobj = AES.new(self.key, AES.MODE_CFB, iv)
	plaintext = encobj.decrypt(ciphertext[AES.block_size:])

	if checksum:
    	    crc, plaintext = (plaintext[-4:], plaintext[:-4])
    	    if not crc == struct.pack("i", zlib.crc32(plaintext)):
        	raise CheckSumError("checksum mismatch")
		#print "crc = " + crc
		#print "calc_crc = " + struct.pack("i", zlib.crc32(plaintext))

	return self._unpad(plaintext)


    def _pad(self, s):
	return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    def _unpad(self, s):
	return s[:-ord(s[len(s)-1:])]

