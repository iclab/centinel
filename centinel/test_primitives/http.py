import ConfigParser
import os
import utils.http as http
import base64
from utils import logger

from centinel.experiment import Experiment


class ConfigurableHTTPRequestExperiment(Experiment):
    name = "config_http"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []
        self.host = None
        self.path = "/"
        self.args = dict()
        self.ssl = False
        self.headers = {}
        self.addHeaders = False

    def run(self):
        parser = ConfigParser.ConfigParser()
        parser.read([self.input_file, ])
        if not parser.has_section('HTTP'):
            return

        self.args.update(parser.items('HTTP'))

        if 'browser' in self.args.keys():
            self.browser = self.args['browser']
            self.addHeaders = True
            if self.browser == "ie" or self.browser == "Internet Explorer":
                self.headers["user-agent"] = "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0)"
            elif self.browser == "Firefox":
                self.headers["user-agent"] = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1"
            elif self.browser == "Chrome" or self.browser == "Google Chrome":
                self.headers["user-agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.56 Safari/537.17"
        for key in self.args.keys():
            if key.startswith("header_"):
                self.addHeaders = True
                value = self.args[key]
                header_key = ""
                split = key.split("header_")
                for x in range(1, len(split)):  # Just in case there are any conflicts in the split or header name
                    header_key += split[x]
                self.headers[header_key] = value

        url_list = parser.items('URLS')

        for url in url_list[0][1].split():
            self.path = '/'
            self.host, self.path = self.get_host_and_path_from_url(url)
            self.whole_url = url
            self.http_request()

    def get_host_and_path_from_url(self, url):
        path = '/'
        temp_url = url
        url_without_http = ""
        host = ""
        if temp_url.startswith("http://") or temp_url.startswith("https://"):
            split_url = temp_url.split("/")
            for x in range(1, len(split_url)):
                if split_url[x] != "":
                    temp_url = split_url[x]
                    host_index = x
                    break
            url_without_http = temp_url
            for x in range(host_index + 1, len(split_url)):
                url_without_http += '/' + split_url[x]
            url_without_http_split = url_without_http.split("/")
            for x in range(1, len(url_without_http_split)):
                if url_without_http_split[x] != '':
                    path += url_without_http_split[x] + '/'
        elif '/' in temp_url:
            split = temp_url.split("/")
            temp_url = split[0]
            if len(split) > 1:
                for x in range(1, len(split)):
                    path += split[x] + '/'

        host = temp_url
        return host, path

    def http_request(self):
        if self.addHeaders:
            result = http.get_request(self.host, self.path, self.headers, self.ssl)
        else:
            result = http.get_request(self.host, self.path, ssl=self.ssl)
        result["whole_url"] = self.whole_url
        result["host"] = self.host
        if "body" not in result["response"]:
            logger.log("e", "No HTTP Response from " + self.whole_url)
            return
        status = result["response"]["status"]
        is_redirecting = str(status).startswith("3") or "location" in result["response"]["headers"]
        result["redirect"] = str(is_redirecting)
        last_redirect = ""
        if is_redirecting:
            all_redirects = [] # Contains dict("string", "string")
            try:
                redirect_number = 1
                redirect_result = None
                while redirect_result is None or (str(redirect_result["response"]["status"]).startswith("3") or "location" in redirect_result["response"]["headers"]):
                    if redirect_number > 50:
                        logger.log("i", "Breaking redirect loop. Over 50 redirects")
                        break
                    if redirect_result is None:
                        redirect_url = result["response"]["headers"]["location"]
                    else:
                        redirect_url = redirect_result["response"]["headers"]["location"]
                    ssl = redirect_url.startswith("https://")
                    if redirect_url == last_redirect:
                        break
                    if last_redirect == "":
                        logger.log("i", "Redirecting from " + self.whole_url + " to " + redirect_url)
                    else:
                        logger.log("i", "Redirecting from " + last_redirect + " to " + redirect_url)
                    host, path = self.get_host_and_path_from_url(redirect_url)
                    redirect_result = http.get_request(host, path, ssl=ssl)
                    temp_results = {}
                    temp_results["headers"] = redirect_result["response"]["headers"]
                    temp_results["status"] = redirect_result["response"]["status"]
                    temp_results["body"] = base64.b64encode(redirect_result["response"]["body"])
                    last_redirect = redirect_url
                    redirect_number += 1
                    all_redirects.append(temp_results)
                if is_redirecting:
                    result["redirects"] = all_redirects
                    result["total_redirects"] = str(redirect_number - 1)

            except Exception as e:
                logger.log("e", "Http redirect failed: " + str(e))
                return
        result["response"]["body"] = base64.b64encode(result["response"]["body"])
        self.results.append(result)