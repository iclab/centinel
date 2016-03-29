import json
import logging
import os
import sys
import time

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

import foctor_core.foctor_core as fc


class HeadlessBrowser:
    def __init__(self):
        self.display = Display(visible=False)
        self.binary = None
        self.profile = None
        self.driver = None
        self.parsed = 0

    @fc.timing
    def setup_profile(self, firebug=True, netexport=True):
        """
        Setup the profile for firefox
        :param firebug: whether add firebug extension
        :param netexport: whether add netexport extension
        :return: a firefox profile object
        """
        capture_path = os.getcwd()
        profile = webdriver.FirefoxProfile()
        profile.set_preference("app.update.enabled", False)
        if firebug:
            profile.add_extension(capture_path + '/extensions/firebug-2.0.8.xpi')
            profile.set_preference("extensions.firebug.currentVersion", "2.0.8")
            profile.set_preference("extensions.firebug.allPagesActivation", "on")
            profile.set_preference("extensions.firebug.defaultPanelName", "net")
            profile.set_preference("extensions.firebug.net.enableSites", True)
            profile.set_preference("extensions.firebug.delayLoad", False)
            profile.set_preference("extensions.firebug.onByDefault", True)
            profile.set_preference("extensions.firebug.showFirstRunPage", False)
            profile.set_preference("extensions.firebug.net.defaultPersist", True)  # persist all redirection responses
        if netexport:
            fc.make_folder(capture_path + "/har/")
            profile.add_extension(capture_path + '/extensions/netExport-0.9b7.xpi')
            profile.set_preference("extensions.firebug.DBG_NETEXPORT", True)
            profile.set_preference("extensions.firebug.netexport.alwaysEnableAutoExport", True)
            profile.set_preference("extensions.firebug.netexport.defaultLogDir", capture_path + "/har/")
            profile.set_preference("extensions.firebug.netexport.includeResponseBodies", True)
        return profile

    def open_virtual_display(self):
        self.display.start()

    def close_virtual_display(self):
        self.display.stop()

    def wrap_results(self, **kwargs):
        """
        Wrap returned http response into a well formatted dict
        :param kwargs (dict): this param should contains following keys:
                                fd: file directory to 
                                url: the test url fo the result
                                files_count: the number of files under har/ directory

        :return (dict): the results of all 
        """

        if 'fd' not in kwargs or \
                        'url' not in kwargs or \
                        'files_count' not in kwargs:
            sys.stderr.write("not enough arguments in wrap_results function\n")
            return {}

        external = kwargs['external'] if 'external' in kwargs else None
        fd = kwargs['fd']
        url = kwargs['url']
        length = kwargs['files_count']

        results = {}

        files = []
        wait_time = 15
        host = self.divide_url(url)[0]
        print host
        time.sleep(0.5)

        # wait until the har file is generated
        while len(os.listdir(fd)) <= length + self.parsed:
            time.sleep(1)
            wait_time -= 1
            if wait_time == 0:
                print "\r%s waiting har file result timeout\n" % url
                results['error'] = "wrap har file timeout"
                if external is not None:
                    external[url] = results
                return results
            sys.stdout.write("\rwaiting for har file... %ds" % (wait_time))
            sys.stdout.flush()
        print ''
        time.sleep(1)

        # find all har files under har/ directory
        for fn in os.listdir(fd):
            if fn.endswith(".har") and fn.startswith(host):
                path = fd + '/' + fn
                files.append((fn, os.stat(path).st_mtime))

        # sort all har files and parse the latest one
        files.sort(key=lambda x: x[1])
        with open(fd + '/' + files[-1][0]) as f:
            raw_data = json.load(f)['log']['entries']
            results = [{} for i in range(0, len(raw_data))]
            for i in range(0, len(results)):

                results[i]['request'] = {}
                results[i]['request']['method'] = raw_data[i]['request']['method']
                headers = {}
                for header in raw_data[i]['request']['headers']:
                    headers[header['name']] = header['value']
                results[i]['request']['headers'] = headers

                results[i]['response'] = {}
                results[i]['response']['status'] = raw_data[i]['response']['status']
                results[i]['response']['reason'] = raw_data[i]['response']['statusText']
                headers = {}
                for header in raw_data[i]['response']['headers']:
                    headers[header['name']] = header['value']
                results[i]['response']['headers'] = headers
                results[i]['response']['redirect'] = raw_data[i]['response']['redirectURL']
                results[i]['response']['body'] = raw_data[i]['response']['content']

                sys.stdout.write("\rstart parsing %s %d%%" % (url, int(100 * (i + 1) / len(results))))
                sys.stdout.flush()
            print "\n"

        self.parsed += 1  # increment the number of parsed har files
        sys.stdout.write('\n\n')
        sys.stdout.flush()

        # save test result of this url to the external result object or 
        # return the result
        if external is not None:
            external[url] = results
        else:
            return results

    def divide_url(self, url):
        """
        divide url into host and path two parts
        """
        if 'https://' in url:
            host = url[8:].split('/')[0]
            path = url[8 + len(host):]
        elif 'http://' in url:
            host = url[7:].split('/')[0]
            path = url[7 + len(host):]
        else:
            host = url.split('/')[0]
            path = url[len(host):]
        return host, path

    def get(self, host, files_count, path="/", ssl=False, external=None):
        """
        Send get request to a url and wrap the results
        :param host (str): the host name of the url
        :param path (str): the path of the url (start with "/")
        :return (dict): the result of the test url
        """
        theme = "https" if ssl else "http"
        url = host + path
        http_url = theme + "://" + url

        result = {}
        try:
            capture_path = os.getcwd() + '/'

            har_file_path = capture_path + "har/"

            # fc.load_page(self.driver, http_url)
            fc.switch_tab(self.driver)
            self.load_page(http_url)

            print "driver get: " + http_url

            time.sleep(2)

            if url[-1] == "/":
                f_name = url.split('/')[-2]
            else:
                f_name = url.split('/')[-1]

            fc.save_html(self.driver, f_name, capture_path + "htmls/")
            fc.save_screenshot(self.driver, f_name, capture_path + "screenshots/")

            result = self.wrap_results(url=http_url, files_count=files_count, fd=har_file_path)

            if external is not None:
                external[http_url] = result

        except Exception as e:
            result['error'] = e.message
            print e

        return result

    def foctor_get_requests(self, site_list_file, results):
        """
        use foctor_core library do get requests
        site_list_file (str): the file name of the list of test urls
                        format: 
                            1, www.facebook.com
                            2, www.google.com
                            ...
        results (dict): the object to save the responses from server
        """

        capture_path = os.getcwd() + "/"
        fc.make_folder(capture_path)

        display_mode = 0  # 0 is virtural display(Xvfb mode)

        site_list = fc.read_site_list(site_list_file=site_list_file, start_index=0, end_index=1 << 31)

        driver, display = fc.do_crawl(sites=site_list, driver=self.driver, display=self.display,
                                      capture_path=capture_path, callback=self.wrap_results,
                                      external=results, fd=capture_path + "har/",
                                      files_count=len(os.listdir(capture_path + "har/")))
        fc.teardown_driver(driver, display, display_mode)

        driver.quit()  # quit driver will also clean up the tmp file under /tmp directory

    def run(self, input_file, url=None, verbose=0):
        """
        run the headless browser with given input
        if url given, the proc will only run hlb with given url and ignore input_list.
        :param url:
        :param input_list:
        :param input_file: the name of the file in "index url" format. i.e.
                1, www.facebook.com
                1, www.google.com
                ...
        :return:
        """
        if not url and not input_file:
            logging.warning("No input file")
            return {"error": "no inputs"}

        results = {}

        self.open_virtual_display()
        if verbose > 0:
            log_file = sys.stdout
        else:
            log_file = None

        # set up firefox driver 
        self.binary = FirefoxBinary(log_file=log_file)
        self.profile = self.setup_profile()
        self.driver = webdriver.Firefox(firefox_profile=self.profile, firefox_binary=self.binary, timeout=60)
        self.driver.set_page_load_timeout(60)
        fc.make_folder(os.getcwd() + "/har/")

        isfile = False
        if url:
            host, path = self.divide_url(url)
            results[url] = self.get(host, path)
        else:
            self.foctor_get_requests(input_file, results)
            isfile = True

        # foctor_core will quit the driver by itself so we only quit the driver when we don't use foctor core
        if not isfile:
            print "quit driver"
            self.quit()
            self.close_virtual_display()

        with open("./hb_results.json", "w") as f:
            json.dump(results, f, indent=4)
        print "Headless browser test finished"
        return results
