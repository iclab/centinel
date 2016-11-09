class UDPset(object):
    def __init__(self, payload, timestamp, c_s_pair, end=False):
        self.payload = payload
        self.timestamp = timestamp
        self.c_s_pair = c_s_pair
        self.end = end

    def __str__(self):
        return '{}--{}--{}--{}'.format(self.payload, self.timestamp, self.c_s_pair, self.end)

    def __repr__(self):
        return '{}--{}--{}--{}'.format(self.payload, self.timestamp, self.c_s_pair, self.end)


class RequestSet(object):
    '''
    NOTE: These objects are created in the parser and the payload is encoded in HEX.
          However, before replaying, the payload is decoded, so for hash and length,
          we need to use the decoded payload.
    '''
    def __init__(self, payload, c_s_pair, response, timestamp):
        self.payload   = payload
        self.c_s_pair  = c_s_pair
        self.timestamp = timestamp

        if response is None:
            self.response_hash = None
            self.response_len  = 0
        else:
            self.response_hash = hash(response.decode('hex'))
            self.response_len  = len(response.decode('hex'))

    def __str__(self):
        return '{} -- {} -- {} -- {}'.format(self.payload, self.timestamp, self.c_s_pair, self.response_len)

class ResponseSet(object):
    '''
    NOTE: These objects are created in the parser and the payload is encoded in HEX.
          However, before replaying, the payload is decoded, so for hash and length,
          we need to use the decoded payload.
    '''
    def __init__(self, request, response_list):
        self.request_len   = len(request.decode('hex'))
        self.request_hash  = hash(request.decode('hex'))
        self.response_list = response_list

    def __str__(self):
        return '{} -- {}'.format(self.request_len, self.response_list)

