import json, logging, base64

from headlesschrome import Client

def get_requests_batch(input_list, results={}):
    for row in input_list:
        results[row['url']] = get_request(row)
    return results

def get_request(http_input):
    url = http_input['url']
    logging.debug("Sending HTTP GET request for %s.".format(url))
    client = Client()
    capture = client.capture(url)
    with open(capture['har'], 'r') as f:
        har = json.load(f, encoding='utf-8')
    with open(capture['screenshot'], 'rb') as f:
        screenshot = 'data:image/png;base64,' + base64.b64encode(f.read())
    return { 'har': har, 'screenshot': screenshot }
