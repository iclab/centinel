import base64
import logging
import threading
import time
import random
import BeautifulSoup
import re
import datetime
import pytz
from urlparse import urlparse

from http_helper import ICHTTPConnection
from centinel.utils import user_agent_pool

REDIRECT_LOOP_THRESHOLD = 5
MAX_THREAD_START_RETRY = 10
THREAD_START_DELAY = 3
CONNECTION_TIMEOUT = 30
REQUEST_TIMEOUT = 60

def meta_redirect(content):
    """
    Returns redirecting URL if there is a HTML refresh meta tag,
    returns None otherwise

    :param content: HTML content
    """
    decoded = content.decode("utf-8", errors="replace")

    try:
        soup = BeautifulSoup.BeautifulSoup(decoded)
    except Exception as e:
        return None

    result = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
    if result:
        try:
            wait, text = result["content"].split(";")
            text = text.strip()
            if text.lower().startswith("url="):
                url = text[4:]
                return url
        except:
            # there are normal meta tag with refresh that are not
            # redirect and don't have a URL in it
            pass
    return None


def _get_http_request(netloc, path="/", headers=None, ssl=False):
    """
    Actually gets the http. Moved this to it's own private method since
    it is called several times for following redirects

    :param host:
    :param path:
    :param headers:
    :param ssl:
    :return:
    """
    if ssl:
        port = 443
    else:
        port = 80

    host = netloc

    if len(netloc.split(":")) == 2:
        host, port = netloc.split(":")

    request = {"host": host,
               "port": port,
               "path": path,
               "ssl": ssl,
               "method": "GET"}
    if headers:
        request["headers"] = headers

    response = {}

    request['startedDateTime'] = datetime.datetime.now(pytz.utc).isoformat()
    try:
        conn = ICHTTPConnection(host=host, port=port, timeout=CONNECTION_TIMEOUT)
        conn.request(path, headers, ssl, timeout=REQUEST_TIMEOUT)
        response["status"] = conn.status
        response["reason"] = conn.reason
        response["headers"] = conn.headers
        body = conn.body

        try:
            response["body"] = body.encode('utf-8')
        except UnicodeDecodeError:
            # if utf-8 fails to encode, just use base64
            response["body.b64"] = body.encode('base64')

    except Exception as err:
        response["failure"] = str(err)

    result = {"response": response,
              "request": request,
              "timings": conn.timings}

    return result


def get_request(netloc, path="/", headers=None, ssl=False,
                external=None, url=None, log_prefix=''):
    http_results = {}

    # Add User-Agent string if not present in headers
    if headers is None:
        headers = {"User-Agent": random.choice(user_agent_pool)}
    elif type(headers) is dict and "User-Agent" not in headers:
        headers["user-Agent"] = random.choice(user_agent_pool)

    first_response = _get_http_request(netloc, path, headers, ssl)
    if "failure" in first_response["response"]:  # If there was an error, just ignore redirects and return
        first_response_information = {"redirect_count": 0,
                                      "redirect_loop": False,
                                      "full_url": url,
                                      "timings": first_response['timings'],
                                      "response": first_response["response"],
                                      "request": first_response["request"]}
        http_results = first_response_information

        if external is not None and type(external) is dict:
            external[url] = http_results
        return http_results

    logging.debug("%sSending HTTP GET request for %s." % (log_prefix, url))

    response_headers_contains_location = False
    location_url = None
    # Checks HTTP Status code and location header to see if the webpage calls for a redirect
    for header, header_value in first_response["response"]["headers"].items():
        if header.lower() == "location":
            response_headers_contains_location = True
            location_url = header_value

    # check meta redirect
    meta_redirect_url = None
    is_meta_redirect = False
    if "body" in first_response["response"]:
        try:
            meta_redirect_url = meta_redirect(first_response["response"]["body"])
        except:
            logging.warning("%sError looking for redirects in: %s." % (log_prefix, url))
    elif "body.b64" in first_response["response"]:
        body_decoded = base64.b64decode(first_response["response"]["body.b64"])
        meta_redirect_url = meta_redirect(body_decoded)

    if meta_redirect_url is not None:
        is_meta_redirect = True

    is_redirecting = response_headers_contains_location or is_meta_redirect


    previous_url = ""
    previous_netloc = netloc
    if is_redirecting:
        http_results["redirects"] = {}
        first_response_information = {"full_url": url,
                                      "timings": first_response['timings'],
                                      "response": first_response["response"],
                                      "request": first_response["request"]}
        http_results["redirects"][0] = first_response_information
        redirect_http_result = None
        redirect_number = 1
        while redirect_http_result is None or is_redirecting and\
                redirect_number <= REDIRECT_LOOP_THRESHOLD:  # While there are more redirects...
            # Usually, redirects that redirect more than 5 times are infinite loops
            if response_headers_contains_location:
                redirect_url = location_url
            elif is_meta_redirect:
                redirect_url = meta_redirect_url

            # prevent looping on the same URL
            if previous_url == redirect_url:
                break
            previous_url = redirect_url

            use_ssl = redirect_url.startswith("https://")  # If redirect url starts with https, use ssl

            # Scheme, query, and fragment aren't used. Urlparse is used here to split the url into the host and path
            # Useful for httplib since it requires this
            parsed_url = urlparse(redirect_url)

            netloc = parsed_url.netloc
            # if host is not specified, use the last one
            if netloc is None or netloc == "":
                netloc = previous_netloc

            previous_netloc = netloc

            redirect_http_result = _get_http_request(netloc, parsed_url.path, ssl=use_ssl)

            # If there is an error in the redirects, break the loop and stop there
            if "failure" in redirect_http_result["response"]:
                http_results["response"] = redirect_http_result["response"]  # This will count as the final response
                break

            response_headers_contains_location = False
            location_url = None
            for header, header_value in redirect_http_result["response"]["headers"].items():
                if header.lower() == "location":
                    response_headers_contains_location = True
                    location_url = header_value

            # check meta redirect
            meta_redirect_url = None
            is_meta_redirect = False
            if "body" in redirect_http_result["response"]:
                meta_redirect_url = meta_redirect(redirect_http_result["response"]["body"])
            elif "body.b64" in redirect_http_result["response"]:
                body_decoded = base64.b64decode(first_response["response"]["body.b64"])
                meta_redirect_url = meta_redirect(body_decoded)

            if meta_redirect_url is not None:
                is_meta_redirect = True

            is_redirecting = response_headers_contains_location or is_meta_redirect

            # If this is the final response, put this in the first request and response json
            if not is_redirecting or redirect_number == REDIRECT_LOOP_THRESHOLD:
                http_results["redirect_loop"] = (is_redirecting and redirect_number ==  REDIRECT_LOOP_THRESHOLD)
                http_results["redirect_count"] = redirect_number
                http_results["full_url"] = redirect_url

            redirect_information = {"full_url": redirect_url,
                                    "timings": first_response['timings'],
                                    "response": redirect_http_result["response"],
                                    "request": redirect_http_result["request"]}
            http_results["redirects"][redirect_number] = redirect_information

            redirect_number += 1

    else:
        first_response_information = {"redirect_count": 0,
                                      "redirect_loop": False,
                                      "full_url": url,
                                      "timings": first_response['timings'],
                                      "response": first_response["response"],
                                      "request": first_response["request"]}
        http_results = first_response_information

    # the external result is used when threading to store
    # the results in the list container provided.
    if external is not None and type(external) is dict:
        external[url] = http_results
    return http_results


def get_requests_batch(input_list, results={}, delay_time=0.5, max_threads=100):
    """
    This is a parallel version of the HTTP GET primitive.

    :param input_list: the input is a list of either dictionaries containing
                       query information, or just domain names (and NOT URLs).
    :param delay_time: delay before starting each thread
    :param max_threads: maximum number of concurrent threads
    :return: results in dict format

    Note: the input list can look like this:
    [
        { "host": "www.google.com",   "path": "/", "headers": {},
          "ssl": False, "url": "http://www.google.com/" },
        "www.twitter.com",
        "www.youtube.com",
        { "host": "www.facebook.com", "path": "/", "headers": {},
          "ssl": True, "url": "http://www.facebook.com" },
        ...
    ]
    """
    threads = []
    thread_error = False
    thread_wait_timeout = 200
    ind = 1
    total_item_count = len(input_list)
    # randomly select one user agent for one input list
    user_agent = random.choice(user_agent_pool)
    for row in input_list:
        headers = {}
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
                if type(row["headers"]) is dict:
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

        if "User-Agent" not in headers:
            headers["User-Agent"] = user_agent

        # add just a little bit of delay before starting the thread
        # to avoid overwhelming the connection.
        time.sleep(delay_time)
        log_prefix = "%d/%d: " % (ind, total_item_count)
        thread = threading.Thread(target=get_request,
                                  args=(host, path, headers, ssl,
                                        results, url, log_prefix))
        ind += 1
        thread.setDaemon(1)

        thread_open_success = False
        retries = 0
        while not thread_open_success and retries < MAX_THREAD_START_RETRY:
            try:
                thread.start()
                threads.append(thread)
                thread_open_success = True
            except:
                retries += 1
                time.sleep(THREAD_START_DELAY)
                logging.error("%sThread start failed for %s, retrying... (%d/%d)" % (log_prefix, url, retries, MAX_THREAD_START_RETRY))

        if retries == MAX_THREAD_START_RETRY:
            logging.error("%sCan't start a new thread for %s after %d retries." % (log_prefix, url, retries))

    for thread in threads:
        thread.join(thread_wait_timeout)

    return results
