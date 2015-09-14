import httplib
import threading
import time
from urlparse import urlparse


def _get_http_request(host, path="/", headers=None, ssl=False,
                external=None, url=None):
    """
    Actually gets the http. Moved this to it's own private method since
    it is called several times for following redirects

    :param host:
    :param path:
    :param headers:
    :param ssl:
    :param external:
    :param url:
    :return:
    """
    request  = {
        "host"  : host,
        "path"  : path,
        "method": "GET"
    }

    response = {}

    try:
        if ssl:
            conn = httplib.HTTPSConnection(host, timeout=10)
            request["ssl"] = True
        else:
            conn = httplib.HTTPConnection(host, timeout=10)
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
    return result


def get_request(host, path="/", headers=None, ssl=False,
                external=None, url=None):
    http_results = {}
    first_response = _get_http_request(host, path, headers, ssl, external, url)
    if "failure" in first_response["response"]:  # If there was an error, just ignore redirects and return
        if external is not None and type(external) is dict:
            external[url] = first_response
        return first_response

    # Checks HTTP Status code and location header to see if the webpage calls for a redirect
    stat_starts_with_3 = str(first_response["response"]["status"]).startswith("3")
    response_headers_contains_location = "location" in first_response["response"]["headers"]

    is_redirecting = stat_starts_with_3 and response_headers_contains_location

    if is_redirecting:
        http_results["request"] = first_response["request"]
        http_results["redirects"] = {}
        first_response_information = {}
        first_response_information["response"] = first_response["response"]
        first_response_information["host"] = host
        first_response_information["path"] = path
        http_results["redirects"]["0"] = first_response_information
        redirect_http_result = None
        redirect_number = 1
        while redirect_http_result is None or (stat_starts_with_3 and response_headers_contains_location) and\
                redirect_number < 6:  # While there are more redirects...
            # Usually, redirects that redirect more than 5 times are infinite loops
            if redirect_http_result is None:  # If it is the first redirect, get url from original http response
                redirect_url = first_response["response"]["headers"]["location"]
            else:  # Otherwise, get the url from the previous redirect
                redirect_url = redirect_http_result["response"]["headers"]["location"]
            use_ssl = redirect_url.startswith("https://")  # If redirect url starts with https, use ssl

            # Scheme, query, and fragment aren't used. Urlparse is used here to split the url into the host and path
            # Useful for httplib since it requires this
            parsed_url = urlparse(redirect_url)
            redirect_http_result = _get_http_request(parsed_url.netloc, parsed_url.path, ssl=use_ssl)
            # The request data is basically repeated throughout each redirect and is the same as in the first
            # request, so it's therefore not needed
            del redirect_http_result["request"]

            # If there is an error in the redirects, break the loop and stop there
            if "failure" in redirect_http_result["response"]:
                http_results["response"] = redirect_http_result["response"]  # This will count as the final response
                break

            stat_starts_with_3 = str(redirect_http_result["response"]["status"]).startswith("3")
            response_headers_contains_location = "location" in redirect_http_result["response"]["headers"]

            # If this is the final response, put this in the first request and response json
            if not stat_starts_with_3 or not response_headers_contains_location:
                http_results["response"] = redirect_http_result["response"]
            else:  # Otherwise, put this in the redirects section
                redirect_information = {}
                redirect_information["host"] = parsed_url.netloc
                redirect_information["path"] = parsed_url.path
                redirect_information["full_url"] = redirect_url
                redirect_information["response"] = redirect_http_result["response"]
                http_results["redirects"][str(redirect_number)] = redirect_information

            redirect_number += 1
    else:
        if external is not None and type(external) is dict:
            external[url] = first_response
        return first_response
    # the external result is used when threading to store
    # the results in the list container provided.
    if external is not None and type(external) is dict:
        external[url] = http_results
    return http_results

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
