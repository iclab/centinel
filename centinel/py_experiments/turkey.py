import centinel.utils.http as http
import centinel.utils.dnslib as dns

from centinel.experiment import Experiment

GOOGLE_DNS     = "8.8.8.8"
SEARCH_STRING  = "home network testbed will appear at"

class TurkeyExperiment(Experiment):
    name = "turkey"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.host = "twitter.com"
        self.path = "/feamster/status/452889624541921280"

    def run(self):
        ips = dns.get_ips(self.host)
        blocked_ips = filter(self.is_blocked, ips)

        if not blocked_ips:
            return

        # let's try using Google's nameserver
        ips = dns.get_ips(self.host, nameserver=GOOGLE_DNS)
        blocked_ips = filter(self.is_blocked, ips)

        if not blocked_ips:
            return

    def is_blocked(self, ip):
        headers = {
            "Host" : self.host
        }

        blocked = True

        try:
            result = http.get_request(ip, self.path, headers, ssl=True)

            blocked = SEARCH_STRING not in result["response"]["body"]
            result["blocked"] = blocked
        except Exception as err:
            result["blocked"] = str(err)

        self.results.append(result)

        return blocked
