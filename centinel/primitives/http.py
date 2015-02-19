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

    return result
