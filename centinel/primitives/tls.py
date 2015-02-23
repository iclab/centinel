# Dependencies: install M2Crypto with sudo apt-get install
# python-m2crypto

import ssl
import M2Crypto


def get_fingerprint(host, port):
    try:
        cert = ssl.get_server_certificate((host, port))
    # if this fails, there's a possibility that SSLv3 handshake was
    # attempted and rejected by the server. Use TLSv1 instead.
    except ssl.SSLError as exp:
        cert = ssl.get_server_certificate((host, port), ssl_version=ssl.PROTOCOL_TLSv1)

    x509 = M2Crypto.X509.load_cert_string(cert, M2Crypto.X509.FORMAT_PEM)
    fingerprint = x509.get_fingerprint('sha1')
    return fingerprint.lower(), cert
