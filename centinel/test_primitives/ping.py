import ConfigParser
import os
import subprocess

from centinel.experiment import Experiment
from utils import logger


class ConfigurablePingExperiment(Experiment):
    name = "config_ping"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.args = dict()

    def run(self):
        parser = ConfigParser.ConfigParser()
        parser.read([self.input_file, ])
        if not parser.has_section('Ping'):
            return

        self.args.update(parser.items('Ping'))
        if 'packets' in self.args.keys():
            self.packets = int(self.args['packets'])
        else:
            self.packets = 1

        if 'timeout' in self.args.keys():
            self.timeout = int(self.args['timeout'])
        else:
            self.timeout = 10

        url_list = parser.items('URLS')
        for url in url_list[0][1].split():
            temp_url = url
            if temp_url.startswith("http://") or temp_url.startswith("https://"):
                split_url = temp_url.split("/")
                for x in range(1, len(split_url)):
                    if split_url[x] != "":
                        temp_url = split_url[x]
                        break
            elif '/' in temp_url:
                temp_url = temp_url.split("/")[0]
            self.host = temp_url
            self.ping_test()

    def ping_test(self):
        result = {
            "host": self.host,
            "packets": self.packets,
            "timeout": self.timeout
        }
        logger.log("i", "Running ping to " + self.host)
        response = os.system("ping -c 1 -W " + str(self.timeout) + " " + self.host + " >/dev/null 2>&1")

        if response == 0:
            result["success"] = 'true'
            # Further experiment
            process = ['ping', self.host, '-c ' + str(self.packets), '-W ' + str(self.timeout)]
            console_response = subprocess.Popen(process, stdout=subprocess.PIPE).communicate()[0]
            ping_data = ""
            rtt_data = ""
            response_lines = []
            for line in console_response.splitlines():
                if "packets transmitted" in line and "received" in line:
                    ping_data = line

                if line.startswith("rtt"):
                    rtt_data = line

                if "bytes from" in line and "icmp_seq" in line:
                    response_lines.append(line)

                if ping_data != "" and rtt_data != "":
                    break

            split_data = ping_data.split()
            packetsTransmitted = -1
            packetsReceived = -1
            packetsLostPercentage = -1  # From 0 - 100
            for x in range(0, len(split_data) - 1):
                if split_data[x] == "packets" and split_data[x + 1].replace(",", "") == "transmitted":
                    packetsTransmitted = int(split_data[x - 1])
                if split_data[x].replace(",", "") == "received":
                    packetsReceived = int(split_data[x - 1])
                if split_data[x].replace(",", "") == "loss" and split_data[x - 1] == "packet":
                    packetsLostPercentage = int(split_data[x - 2].replace("%", ""))
            split_data = rtt_data.split()
            for string in split_data:
                if '/' in string and '.' in string:
                    rtt_split = string.split('/')
                    result["rtt_min"] = rtt_split[0]
                    result["rtt_avg"] = rtt_split[1]
                    result["rtt_max"] = rtt_split[2]
            if len(response_lines) > 0:
                response_data = response_lines[0].split()
                for part in response_data:
                    if part.startswith("ttl"):
                        result["ttl"] = part.split("=")[1]
            result["sent"] = str(packetsTransmitted)
            result["received"] = str(packetsReceived)
            result["percent_lost"] = str(packetsLostPercentage)
        else:
            result["success"] = 'false'
        self.results.append(result)
