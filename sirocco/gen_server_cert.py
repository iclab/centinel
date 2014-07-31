from OpenSSL import crypto, SSL
from socket import gethostname
from pprint import pprint
from time import gmtime, mktime
from os.path import exists, join

def create_self_signed_cert(cert_file, key_file):
    C_F = cert_file #join(cert_dir, CERT_FILE)
    K_F = key_file  #join(cert_dir, KEY_FILE)

    if not exists(C_F) or not exists(K_F):
	# create a self-signed cert
	cert = crypto.X509()
	cert.get_subject().C = "US" #raw_input("Country: ")
	cert.get_subject().ST = "New York" #raw_input("State: ")
	cert.get_subject().L = "Stony Brook" #raw_input("City: ")
	cert.get_subject().O = "Stony Brook University" #raw_input("Organization: ")
	cert.get_subject().OU = "The ICLab" #raw_input("Organizational Unit: ")
	cert.get_subject().CN = "nrg.cs.stonybrook.edu"
	cert.set_serial_number(1000)
	cert.gmtime_adj_notBefore(0)
	cert.gmtime_adj_notAfter(315360000)
	cert.set_issuer(cert.get_subject())
	# create a key pair
	k = crypto.PKey()
	k.generate_key(crypto.TYPE_RSA, 1024)

	cert.set_pubkey(k)
	cert.sign(k, 'sha1')
	open(C_F, "wt").write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
	open(K_F, "wt").write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
