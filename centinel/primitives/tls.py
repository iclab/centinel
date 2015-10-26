# Dependencies: install M2Crypto with sudo apt-get install
# python-m2crypto

import logging

try:
    import M2Crypto
    m2crypto_imported = True
except:
    logging.warning("M2Crypto could not be imported. "
                    "TLS fingerprinting will be disabled.")
    m2crypto_imported = False

import ssl
import threading
import time


def get_fingerprint(host, port=443, external=None, log_prefix=''):
    tls_error = None
    fingerprint_error = None
    cert = None

    logging.debug("%sGetting TLS certificate "
                  "for %s:%d." % (log_prefix, host, port))

    try:
        cert = ssl.get_server_certificate((host, port),
                                          ssl_version=ssl.PROTOCOL_TLSv1)
    # if this fails, there's a possibility that SSLv3 handshake was
    # attempted and rejected by the server. Use TLSv1 instead.
    except ssl.SSLError:
        # exception could also happen here
        try:
            cert = ssl.get_server_certificate((host, port),
                                              ssl_version=ssl.PROTOCOL_SSLv23)
        except Exception as exp:
            tls_error = str(exp)
    except Exception as exp:
        tls_error = str(exp)

    # this comes out as unicode, but m2crypto breaks if it gets
    # something other than a string, so convert to ascii
    if type(cert) == unicode:
        cert = cert.encode('ascii', 'ignore')

    if tls_error is None and m2crypto_imported:
        try:
            x509 = M2Crypto.X509.load_cert_string(cert,
                                                  M2Crypto.X509.FORMAT_PEM)
            fingerprint = x509.get_fingerprint('sha1')
        except Exception as exp:
            fingerprint_error = str(exp)

    if not m2crypto_imported:
        fingerprint_error = "M2Crypto could not be imported."

    # the external result is used when threading to store
    # the results in the list container provided.
    row = "%s:%s" % (host, port)

    # handle return value based on exception types
    if tls_error is None and fingerprint_error is None:
        if external is not None and type(external) is dict:
            external[row] = {"cert": cert,
                             "fingerprint": fingerprint.lower()}
        return fingerprint.lower(), cert
    elif tls_error is None and fingerprint_error is not None:
        if external is not None and type(external) is dict:
            external[row] = {"cert": cert,
                             "fingerprint_error": fingerprint_error}
        return fingerprint_error, cert
    else:
        if external is not None and type(external) is dict:
            external[row] = {"tls_error": tls_error,
                             "fingerprint_error": fingerprint_error}
        return fingerprint_error, tls_error


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
    thread_error = False
    thread_wait_timeout = 200
    ind = 1
    total_item_count = len(input_list)
    for row in input_list:
        if len(row.split(":")) == 2:
            host, port = row.split(":")
        elif len(row.split(":")) == 1:
            host = row
            port = default_port
        else:
            continue

        port = int(port)
        wait_time = 0
        while threading.active_count() > max_threads:
            time.sleep(1)
            wait_time += 1
            if wait_time > thread_wait_timeout:
                thread_error = True
                break

        if thread_error:
            results["error"] = "Threads took too long to finish."
            break

        # add just a little bit of delay before starting the thread
        # to avoid overwhelming the connection.
        time.sleep(delay_time)

        log_prefix = "%d/%d: " % (ind, total_item_count)
        thread = threading.Thread(target=get_fingerprint,
                                  args=(host, port,
                                        results, log_prefix))
        ind += 1
        thread.setDaemon(1)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join(thread_wait_timeout)

    return results
