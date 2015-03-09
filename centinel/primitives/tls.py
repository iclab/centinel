# Dependencies: install M2Crypto with sudo apt-get install
# python-m2crypto

import M2Crypto
import ssl
import threading
import time


def get_fingerprint(host, port=443, external=None):
    try:
        cert = ssl.get_server_certificate((host, port))
    # if this fails, there's a possibility that SSLv3 handshake was
    # attempted and rejected by the server. Use TLSv1 instead.
    except ssl.SSLError as exp:
        cert = ssl.get_server_certificate((host, port),
                                          ssl_version=ssl.PROTOCOL_TLSv1)

    x509 = M2Crypto.X509.load_cert_string(cert, M2Crypto.X509.FORMAT_PEM)
    fingerprint = x509.get_fingerprint('sha1')
    # the external result is used when threading to store
    # the results in the list container provided.
    if external is not None and type(external) is dict:
        row = "%s:%s" % (host, port)
        external[row] = { "cert": cert,
                          "fingerprint": fingerprint.lower() }

    return fingerprint.lower(), cert


def get_fingerprint_batch(input_list, default_port=443,
                          delay_time=0.5, max_threads=100):
    """
    This is a parallel version of the TLS fingerprint primitive.

    Params:
    input_list-   the input is a list of host:ports.
    default_port- default port to use when no port specified
    delay_time-   delay before starting each thread
    max_threads-  maximum number of concurrent threads

    """
    results = {}
    threads = []
    for row in input_list:
        if len(row.split(":")) == 2:
            host, port = row.split(":")
        elif len(row.split(":")) == 1:
            host = row
            port = default_port
        else:
            continue

        port = int(port)
        while threading.active_count() > max_threads:
            time.sleep(1)

        # add just a little bit of delay before starting the thread
        # to avoid overwhelming the connection.
        time.sleep(delay_time)

        thread = threading.Thread(target=get_fingerprint,
                                  args=(host, port, results))
        thread.setDaemon(1)
        thread.start()
        threads.append(thread)

    threads[-1].join(10)

    return results
