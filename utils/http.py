import httplib

def get_request(host, path="/", headers=None, ssl=False):
    request  = {
        "host"  : host,
        "path"  : path,
        "method": "GET"
    }

    response = {}

    try:
        if ssl:
            conn = httplib.HTTPSConnection(host)
        else:
            conn = httplib.HTTPConnection(host)

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
        response["body"] = body

        conn.close()
    except Exception as err:
        response["failure"] = str(err)

    result = {
        "response" : response,
        "request"  : request
    }

    return result
