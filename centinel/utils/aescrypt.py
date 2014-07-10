import zlib
import struct
import base64
from Crypto.Cipher import AES
from Crypto import Random

class CheckSumError(Exception):
    pass

def _lazysecret(secret, blocksize=32, padding='}'):
    """pads secret if not legal AES block size (16, 24, 32)"""
    if not len(secret) in (16, 24, 32):
        return secret + (blocksize - len(secret)) * padding
    return secret

def encrypt(plaintext, secret, lazy=True, checksum=True):
    """encrypt plaintext with secret
    plaintext   - content to encrypt
    secret      - secret to encrypt plaintext
    lazy        - pad secret if less than legal blocksize (default: True)
    checksum    - attach crc32 byte encoded (default: True)
    returns ciphertext
    """

    secret = _lazysecret(secret) if lazy else secret
    iv = Random.new().read(AES.block_size)
    encobj = AES.new(secret, AES.MODE_CFB, iv)

    if checksum:
        plaintext += struct.pack("i", zlib.crc32(plaintext))

    return encobj.encrypt(plaintext)

def decrypt(ciphertext, secret, lazy=True, checksum=True):
    """decrypt ciphertext with secret
    ciphertext  - encrypted content to decrypt
    secret      - secret to decrypt ciphertext
    lazy        - pad secret if less than legal blocksize (default: True)
    checksum    - verify crc32 byte encoded checksum (default: True)
    returns plaintext
    """

    secret = _lazysecret(secret) if lazy else secret
    iv = Random.new().read(AES.block_size)
    encobj = AES.new(secret, AES.MODE_CFB, iv)
    plaintext = encobj.decrypt(ciphertext)

    if checksum:
        crc, plaintext = (plaintext[-4:], plaintext[:-4])
        if not crc == struct.pack("i", zlib.crc32(plaintext)):
            raise CheckSumError("checksum mismatch")

    return plaintext

class AESCipher:

    def __init__(self, key):
	self.bs = 32
	if len(key) >= 32:
    	    self.key = key[:32]
	else:
    	    self.key = self._pad(key)

    def xencrypt(self, raw):
	raw = self._pad(raw)
	iv = Random.new().read(AES.block_size)
	cipher = AES.new(self.key, AES.MODE_CBC, iv)
	return base64.b64encode(iv + cipher.encrypt(raw))
    
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

    def xdecrypt(self, enc):
	enc = base64.b64decode(enc)
	iv = enc[:AES.block_size]
	cipher = AES.new(self.key, AES.MODE_CBC, iv)
	return self._unpad(cipher.decrypt(enc[AES.block_size:]))

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


#encd = cphr.encrypt(open("x.jpg", 'r').read())
#decd = cphr.decrypt(encd)
#open("decd.jpg", "w").write(decd)

