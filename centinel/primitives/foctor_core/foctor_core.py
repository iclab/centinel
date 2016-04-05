__author__ = 'rishabn'

import signal
import errno
import sys
import logging

from foctor_misc import *
from foctor_search import *
from foctor_authentication import *

from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, ElementNotVisibleException, NoSuchElementException, \
    ElementNotSelectableException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from httplib import CannotSendRequest
from selenium.common.exceptions import StaleElementReferenceException

from functools import wraps
from pyvirtualdisplay import Display


def teardown_driver(driver_, display_, display_mode):
    driver_.close()
    if display_mode == 0:
        display_.stop()


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        logging.debug('%s : %0.5f s' % (f.func_name, (time2 - time1)))
        return ret
    return wrap


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decorator


def read_site_list(site_list_file, start_index, end_index, login_mode=False):
    sites = list()
    f = open(site_list_file)
    for line in f:
        index, url = line.split(",")[0].strip(), line.split(",")[1].strip()
        if (int(index) <= end_index) and (int(index) >= start_index):
            if login_mode is True:
                uname, password = line.split(",")[2].strip(), line.split(",")[3].strip()
                sites.append([index, url, uname, password])
            else:
                sites.append([index, url])
    sites.sort(key=lambda x: int(x[0]))
    return sites


@timeout(10)
def save_screenshot(driver, filename, path):
    make_folder(path)
    ss_path = path + str(filename) + ".png"
    done = False
    while done is False:
        try:
            driver.save_screenshot(ss_path)
            done = True
        except CannotSendRequest:
            done = False
            time.sleep(1)
        except (TimeoutError, TimeoutException):
            logging.warning("save_screenshot() timed out")
            return "Timed-out"
    return "No Error"


@timeout(10)
def save_html(driver, filename, path):
    make_folder(path)
    html_path = path + str(filename) + ".html"
    f = open(html_path, "w")
    done = False
    while done is False:
        try:
            f.write(driver.page_source.encode("UTF-8"))
            done = True
        except CannotSendRequest:
            done = False
            time.sleep(1)
        except (TimeoutError, TimeoutException):
            logging.warning("save_html() timed out")
            return "Timed-out"
    f.close()
    return "No Error"


@timeout(60)
def wait_for_ready_state(driver, time_, state):
    time.sleep(1)
    try:
        WebDriverWait(driver, int(time_)).until(lambda d: d.execute_script('return document.readyState') == state)
    except (TimeoutError, TimeoutException):
        return "Timed-out"


def setup_profile(tor=False, port="9000", firebug=True, netexport=True, noscript=False, capture_path="", cache_enabled=True):
    profile = webdriver.FirefoxProfile()
    profile.set_preference("app.update.enabled", False)
    if tor is True:
        profile.set_preference('network.proxy.type', 1)
        profile.set_preference('network.proxy.socks', "127.0.0.1")
        profile.set_preference('network.proxy.socks_port', int(port))
    if cache_enabled is False:
        profile.set_preference("browser.cache.disk.enable", False)
        profile.set_preference("browser.cache.memory.enable", False)
        profile.set_preference("browser.cache.offline.enable", False)
        profile.set_preference("network.http.use-cache", False)
        profile.set_preference("browser.cache.disk_cache_ssl", False)
    if firebug is True:
        profile.add_extension("./extensions/firebug-2.0.8.xpi")
        profile.set_preference("extensions.firebug.currentVersion", "2.0.8")
        profile.set_preference("extensions.firebug.allPagesActivation", "on")
        profile.set_preference("extensions.firebug.defaultPanelName", "net")
        profile.set_preference("extensions.firebug.net.enableSites", True)
        profile.set_preference("extensions.firebug.delayLoad", False)
        profile.set_preference("extensions.firebug.onByDefault", True)
        profile.set_preference("extensions.firebug.showFirstRunPage", False)
        profile.set_preference("extensions.firebug.net.defaultPersist", True)
    if netexport is True:
        profile.add_extension('./extensions/netExport-0.9b7.xpi')
        profile.set_preference("extensions.firebug.netexport.alwaysEnableAutoExport", True)
        make_folder(capture_path+"/har/")
        profile.set_preference("extensions.firebug.netexport.defaultLogDir", capture_path+"/har/")
    if noscript is True:
        profile.add_extension('./extensions/noscript-2.6.9.3.xpi')
        profile.set_preference('noscript.firstRunRedirection', False)
        profile.set_preference("capability.policy.maonoscript.javascript.enabled", "allAccess")
        profile.set_preference("capability.policy.maonoscript.sites", "about:chrome:resource:")
        profile.set_preference("noscript.ABE.enabled", False)
        profile.set_preference("noscript.ABE.notify", False)
        profile.set_preference("noscript.ABE.wanIpAsLocal", False)
        profile.set_preference("noscript.confirmUnblock", False)
        profile.set_preference("noscript.contentBlocker", True)
        profile.set_preference("noscript.default", "about: chrome:resources:")
        profile.set_preference("noscript.firstRunRedirection", False)
        profile.set_preference("noscript.global", True)
        profile.set_preference("noscript.gtemp", "")
        profile.set_preference("noscript.opacizeObject", 3)
        profile.set_preference("noscript.forbidWebGL", True)
        profile.set_preference("noscript.forbidFonts", False)
        profile.set_preference("noscript.options.tabSelectedIndexes", "5,0,0")
        profile.set_preference("noscript.policynames", "")
        profile.set_preference("noscript.secureCookies", True)
        profile.set_preference("noscript.showAllowPage", False)
        profile.set_preference("noscript.showBaseDomain", False)
        profile.set_preference("noscript.showDistrust", False)
        profile.set_preference("noscript.showRecentlyBlocked", False)
        profile.set_preference("noscript.showTemp", False)
        profile.set_preference("noscript.showTempToPerm", False)
        profile.set_preference("noscript.showUntrusted", False)
        profile.set_preference("noscript.STS.enabled", False)
        profile.set_preference("noscript.subscription.lastCheck", -142148139)
        profile.set_preference("noscript.temp", "")
        profile.set_preference("noscript.untrusted", "")
        profile.set_preference("noscript.forbidMedia", True)
        profile.set_preference("noscript.forbidFlash", True)
        profile.set_preference("noscript.forbidSilverlight", True)
        profile.set_preference("noscript.forbidJava", True)
        profile.set_preference("noscript.forbidPlugins", True)
        profile.set_preference("noscript.showPermanent", False)
        profile.set_preference("noscript.showTempAllowPage", True)
        profile.set_preference("noscript.showRevokeTemp", True)
        profile.set_preference("noscript.notify", False)
        profile.set_preference("noscript.autoReload", False)
        profile.set_preference("noscript.autoReload.allTabs", False)
        profile.set_preference("noscript.cascadePermissions", True)
        profile.set_preference("noscript.restrictSubdocScripting", True)
        profile.set_preference("noscript.ABE.migration", 1)
        profile.set_preference("noscript.cascadePermissions", False)
        profile.set_preference("noscript.forbidBookmarklets", True)
        profile.set_preference("noscript.forbidMetaRefresh", True)
        profile.set_preference("noscript.global", False)
        profile.set_preference("noscript.nselForce", False)
        profile.set_preference("noscript.nselNever", True)
        profile.set_preference("noscript.options.tabSelectedIndexes", "5,5,0")
        profile.set_preference("noscript.subscription.lastCheck", 1137677561)
        profile.set_preference("noscript.version", "2.6.9.2")
    return profile


def restart_driver(driver_, display_, tor=False, tor_call="", display_mode=0, capture_path="", port="9000",
                   process_tag="1", exits="US"):
    teardown_driver(driver_, display_, display_mode)
    time.sleep(5)
    if tor is True:
        logging.info("Killing old Tor process...")
        for i in range(0, 10):
            command = "ps -ef | grep \"" + tor_call + "\" | grep -v \"grep\" | awk '{print $2}' | xargs kill"
            os.system(command)
            time.sleep(1)
    return crawl_setup(tor=tor, capture_path=capture_path, display_mode=display_mode, port=port,
                       process_tag=process_tag, exits=exits)


def crawl_setup(tor=False, capture_path="", display_mode=0, port="9000", process_tag="1", exits="US"):
    tor_call = ""
    make_folder(capture_path)
    if tor is True:
        profile_ = setup_profile(tor=True, port=port, firebug=True, netexport=True, noscript=False,
                                 capture_path=capture_path)
        torrc_file = create_tor_config(port, "./torrc-" + process_tag, exits)
        tor_call = start_program("/usr/sbin/tor -f " + torrc_file)
    else:
        profile_ = setup_profile(firebug=True, netexport=True, noscript=False, capture_path=capture_path)
    display_ = Display(visible=0, size=(1024, 768))
    if display_mode == 0:
        display_.start()
    binary = FirefoxBinary("./firefox/firefox")
    driver_ = webdriver.Firefox(firefox_profile=profile_, firefox_binary=binary)
    driver_.set_page_load_timeout(60)
    driver_.set_script_timeout(60)
    return driver_, display_, tor_call


def load_login_actions(playback_file, website):
    p = open(playback_file, "r")
    actions = list()
    for line in p:
        line = line.split(",")
        if len(line) < 9:
            continue
        for i in range(0, len(line)):
            line[i] = line[i].strip()
        action = dict()
        action['index'], action['url'], action['action'] = line[0], line[1], line[2]
        action['text'], action['name'], action['id'] = line[3], line[4], line[5]
        action['aria'], action['label'], action['tag'] = line[6], line[7], line[8]
        if line[1] == website:
            actions.append(action)
    return actions


def do_playback(credentials, playback_file, driver, display, capture_path="", process_tag="1", tor=False, tor_call="",
                display_mode=0, port="9000", exits="US"):
    status_file = capture_path + "/status-" + process_tag
    status_log_file = capture_path + "/log-" + process_tag
    slf = open(status_log_file, "a")
    for c in credentials:
        status_code = load_page(driver=driver, url=c[1], cookies=0)
        str_status = "Loading URL: " + str(c[1]) + " \t Index: " + str(c[0]) + " \t " + str(status_code)
        logging.debug(str_status)
        sf = open(status_file, "w")
        sf.write(str(c[0]))
        sf.flush()
        sf.close()
        slf.write(str_status)
        slf.flush()
        html_status, ss_status = "No Error", "No Error"
        if str(status_code) == "No Error":
            actions = load_login_actions(playback_file=playback_file, website=c[1])
            if len(actions) == 0:
                logging.warning("Unable to find a playback log for " + c[1])
            for a in actions:
                save_name = str(c[0]) + "-" + str(process_tag)
                make_folder(capture_path)
                save_html(driver, save_name, capture_path+"/htmls/")
                save_screenshot(driver, save_name, capture_path+"/screenshots/")
                time.sleep(1)
                e = find_element_by_record(driver, a)
                if e is None:
                    logging.warning("EE. Playback Failed. Site: " + c[1])
                    driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, port,
                                                 exits)
                    break
                if a['action'] == "click":
                    try:
                        e.click()
                    except (StaleElementReferenceException, NoSuchElementException, ElementNotSelectableException,
                            ElementNotVisibleException):
                        logging.warning("CE. Playback Failed. Site: " + c[1])
                        driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, port,
                                                     exits)
                        break
                    status = wait_for_ready_state(driver, 30, "complete")
                    if status == "Timed-out":
                        break
                if a['action'] == "username":
                    try:
                        e.send_keys(c[2])
                    except (StaleElementReferenceException, NoSuchElementException, ElementNotSelectableException,
                            ElementNotVisibleException):
                        logging.warning("UN. Playback Failed. Site: " + c[1])
                        driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, port,
                                                     exits)
                        break
                if a['action'] == "password":
                    try:
                        e.send_keys(c[3])
                        e.send_keys(Keys.RETURN)
                    except (StaleElementReferenceException, NoSuchElementException, ElementNotSelectableException,
                            ElementNotVisibleException):
                        logging.warning("PW. Playback Failed. Site: " + c[1])
                        driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, port,
                                                     exits)
                        break
                    status = wait_for_ready_state(driver, 30, "complete")
                    if status == "Timed-out":
                        driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, port,
                                                     exits)
                        break
            save_name = str(c[0]) + "-" + str(process_tag)
            make_folder(capture_path)
            html_status = save_html(driver, save_name, capture_path)
            ss_status = save_screenshot(driver, save_name, capture_path)
            time.sleep(1)
        if (str(status_code) != "No Error") or (str(ss_status) != "No Error") or (str(html_status) != "No Error"):
            driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, process_tag, port, exits)
            logging.debug(str_status)
            slf.write("Restarting driver (tor call: " + tor_call + ")\n")
            continue
    sf = open(status_file, "w")
    sf.write(str("C"))
    sf.flush()
    sf.close()
    slf.close()
    return driver, display


def abort_load(driver, display, tor, tor_call, display_mode, capture_path, process_tag, port, exits):
    logging.debug("Aborting page load...")
    not_closed = True
    while not_closed:
        try:
            driver, display, tor_call = restart_driver(driver, display, tor, tor_call, display_mode, capture_path,
                                                       port, process_tag, exits)
            not_closed = False
            time.sleep(10)
        except CannotSendRequest:
            not_closed = True
    return driver, display


def do_crawl(sites, driver, display, capture_path="", tor=False, tor_call="", search=False, search_log="",
             login_full=False, login_part=False, login_log="", display_mode=0, process_tag="1", port="9000",
             exits="US", callback=None, **kwargs):
    for s in sites:
        status_code = load_page(driver=driver, url=s[1], cookies=0)
        str_status = "Loading URL: " + str(s[1]) + " \t Index: " + str(s[0]) + " \t " + str(status_code) + "\n"
        logging.debug(str_status)
        html_status, ss_status = "No Error", "No Error"
        if str(status_code) == "No Error":
            # save_name = str(s[0]) + "-" + str(process_tag)
            # html_status = save_html(driver, save_name, os.path.join(capture_path, 'htmls/'))
            # ss_status = save_screenshot(driver, save_name, os.path.join(capture_path, 'screenshots/'))
            time.sleep(1)
            if search is True:
                rule = find_search_rule(driver)
                f = open(search_log, "a")
                f.write(str(s[0]) + ", \t" + str(s[1]) + ", \t" + str(rule) + "\n")
                f.flush()
                f.close()
            elif login_full is True:
                login_elements = record_login_elements(driver, uname=str(s[2]), password=str(s[3]))
                f = open(login_log, "a")
                if login_elements is not None:
                    for le in login_elements:
                        f.write(str(s[0]) + ", \t" + str(s[1]) + ", \t" + str(le) + "\n")
                    f.flush()
                    f.close()
            elif login_part is True:
                if front_page_login(driver) is True:
                    f = open(login_log, "a")
                    f.write(str(s[0]) + ", \t" + str(s[1]) + "\n")
                    f.flush()
                    f.close()
        if (str(status_code) != "No Error") or (str(ss_status) != "No Error") or (str(html_status) != "No Error"):
            driver, display = abort_load(driver, display, tor, tor_call,
                                         display_mode, capture_path, process_tag, port, exits)
            logging.debug(str_status)
            continue
        if callback is not None:
            callback(index=s[0], url=s[1], **kwargs)
    return driver, display


def switch_tab(driver):
    main_window = driver.current_window_handle
    body = driver.find_element_by_tag_name("body")
    # body.send_keys(Keys.CONTROL + 't')
    body.send_keys(Keys.CONTROL + 't')
    driver.switch_to_window(main_window)
    body_tab = driver.find_element_by_tag_name("body")
    time.sleep(.5)
    if body == body_tab:
        logging.warning("Switch tab failed")
    else:
        body_tab.send_keys(Keys.CONTROL + Keys.TAB)
        driver.switch_to_window(main_window)
        body = driver.find_element_by_tag_name("body")
        body.send_keys(Keys.CONTROL + 'w')
        driver.switch_to_window(main_window)
        body_tab = driver.find_element_by_tag_name("body")
        body_tab.send_keys(Keys.CONTROL + Keys.TAB)
        driver.switch_to_window(main_window)
        body = driver.find_element_by_tag_name("body")
        if body != body_tab:
            logging.warning("Failed to switch tab, switch back to previous tab")


@timeout(60)
def load_page(driver, url, cookies=0):
    try:
        if cookies == 0:
            driver.delete_all_cookies()
            time.sleep(1)
        if "http" not in url.split("/")[0]:
            url = "http://" + url

        switch_tab(driver)
        driver.get(url)

        logging.debug("driver.get(%s) returned successfully" % url)
    except (TimeoutException, TimeoutError) as te:
        logging.warning("Loading %s timed out" % url)
        return str(te)
    # try:
    #     element = WebDriverWait(driver, .5).until(EC.alert_is_present())
    #     if element is not None:
    #         print "Alert found on page: " + url
    #         sys.stdout.flush()
    #         raise TimeoutError
    #     else:
    #         raise NoAlertPresentException
    # except (TimeoutException, NoAlertPresentException):
    #     print "No alert found on page: " + url
    #     sys.stdout.flush()
    #     pass
    # except TimeoutError as te:
    #     sys.stdout.flush()
    #     return str(te)
    # try:
    #     main_handle = driver.current_window_handle
    # except CannotSendRequest as csr:
    #     return str(csr)
    try:
        windows = driver.window_handles
        if len(windows) > 1:
            logging.debug("Pop up detected on page: %s. Closing driver instance." % url)
            raise TimeoutError
            # for window in windows:
            #     if window != main_handle:
            #         driver.switch_to_window(window)
            #         driver.close()
            # driver.switch_to_window(main_handle)
        # wfrs_status = wait_for_ready_state(driver, 15, 'complete')
        # if wfrs_status == "Timed-out":
        #     print "wait_for_ready_state() timed out."
        #     raise TimeoutError
    except (TimeoutException, TimeoutError) as te:
        logging.warning("Loading %s timed out" % url)
        return str(te)
    return "No Error"


def do_search(rules, driver, display, capture_path="", tor=False, tor_call="", display_mode=0, process_tag="1",
              port="9000", exits="US", term="Stony Brook University"):
    status_file = capture_path + "/status-" + process_tag
    status_log_file = capture_path + "/log-" + process_tag
    slf = open(status_log_file, "a")
    for r in rules:
        status_code = load_page(driver=driver, url=r['url'], cookies=0)
        str_status = "Loading URL: " + str(r['url']) + " \t Index: " + str(r['index']) + " \t " + str(status_code)
        logging.debug(str_status)
        slf.write(str_status)
        slf.flush()
        sf = open(status_file, "w")
        sf.write(str(r['index']))
        sf.flush()
        sf.close()
        html_status, ss_status = "No Error", "No Error"
        time.sleep(.5)
        if str(status_code) == "No Error":
            try:
                element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, r['id'])))
                element.send_keys(term)
                element.send_keys(Keys.RETURN)
                time.sleep(3)
            except (ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException,
                    TimeoutError, TimeoutException) as exception:
                logging.warning("Could not complete search: " + str(exception))
            save_name = str(r['index']) + "-" + str(process_tag)
            make_folder(capture_path)
            html_status = save_html(driver, save_name, capture_path)
            ss_status = save_screenshot(driver, save_name, capture_path)
            time.sleep(.5)
        if (str(status_code) != "No Error") or (str(ss_status) != "No Error") or (str(html_status) != "No Error"):
            driver, display = abort_load(driver, display, tor, tor_call, display_mode, capture_path, process_tag, port, exits)
            logging.debug(str_status)
            slf.write("Restarting driver (tor call: " + tor_call + ")\n")
            continue
    sf = open(status_file, "w")
    sf.write("C")
    sf.flush()
    sf.close()
    slf.close()
    return driver, display


