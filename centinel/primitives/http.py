import httplib
import threading
import time

def get_request(host, path="/", headers=None, ssl=False,
                external=None, url=None):
    request  = {
        "host"  : host,
        "path"  : path,
        "method": "GET"
    }

    response = {}

    try:
        if ssl:
            conn = httplib.HTTPSConnection(host)
            request["ssl"] = True
        else:
            conn = httplib.HTTPConnection(host)
            request["ssl"] = False
        if headers:
            conn.request("GET", path, headers=headers)
        else:
            conn.request("GET", path)

        resp = conn.getresponse()
        response["status"] = resp.status
        response["reason"] = resp.reason

        headers = dict(resp.getheaders())
        response["headers"] = headers

        body = resp.read()
        try:
            body.encode('utf8')
            response["body"] = body
        except UnicodeDecodeError as err:
            # if utf-8 fails to encode, just use base64
            response["body.b64"] = body.encode('base64')

        conn.close()
    except Exception as err:
        response["failure"] = str(err)

    result = {
        "response" : response,
        "request"  : request
    }
    # the external result is used when threading to store
    # the results in the list container provided.
    if external is not None and type(external) is dict:
        external[url] = result
    return result

def get_requests_batch(input_list, delay_time=0.5, max_threads=100):
    """
    This is a parallel version of the HTTP GET primitive.

    Params:
    input_list- the input is a list of either dictionaries containing
                query information, or just domain names (and NOT URLs).
    delay_time- delay before starting each thread
    max_threads- maximum number of concurrent threads

    Note: the input list can look like this:
    [
        { "host": "www.google.com",   "path": "/", "headers": [],
          "ssl": False, "url": "http://www.google.com/" },
        "www.twitter.com",
        "www.youtube.com",
        { "host": "www.facebook.com", "path": "/", "headers": [],
          "ssl": True, "url": "http://www.facebook.com" },
        ...
    ]

    """
    results = {}
    threads = []
    thread_error = False
    thread_wait_timeout = 200
    for row in input_list:
        headers = []
        path = "/"
        ssl = False
        theme = "http"
        if type(row) is dict:
            if "host" not in row:
                continue
            host = row["host"]

            if "path" in row:
                path = row["path"]

            if "headers" in row:
                if type(row["headers"]) is list:
                    headers = row["headers"]

            if "ssl" in row:
                ssl = row["ssl"]
                theme = "https"

            if "url" in row:
                url = row["url"]
            else:
                url = "%s://%s%s" % (theme, host, path)
        else:
            host = row
            url = "%s://%s%s" % (theme, host, path)

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

        thread = threading.Thread(target=get_request,
                                  args=(host, path, headers, ssl,
                                        results, url))
        thread.setDaemon(1)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join(thread_wait_timeout)

    return results
