# Dependencies: install M2Crypto with sudo apt-get install
# python-m2crypto

import ssl
import M2Crypto


def get_fingerprint(host, port):
    cert = ssl.get_server_certificate((host, port))
    x509 = M2Crypto.X509.load_cert_string(cert, M2Crypto.X509.FORMAT_PEM)
    fingerprint = x509.get_fingerprint('sha1')
    return fingerprint.lower(), cert
