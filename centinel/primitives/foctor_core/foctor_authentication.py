__author__ = 'rishabn'

import time
import signal
import errno
import os
from functools import wraps

from selenium.common.exceptions import StaleElementReferenceException, ElementNotSelectableException, \
    NoSuchElementException, ElementNotVisibleException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def set_union(list_of_lists):
    l_l = list_of_lists
    union = list()
    for l in l_l:
        set_l = set(l)
        for item in set_l:
            union.append(item)
    return set(union)


def compare_record(rec_1, rec_2):
    if rec_1 is None:
        if rec_2 is None:
            return 1
        else:
            return -1
    if rec_2 is None:
        if rec_1 is None:
            return 1
        else:
            return -1
    if rec_1 == rec_2:
        return 1
    else:
        return -1


def get_record(element, tag):
    if element is None:
        return None
    else:
        try:
            te, record = element, {}
            record['tag'] = tag
            record['title'] = unicode(te.get_attribute("title"))
            record['type'] = unicode(te.get_attribute("type"))
            record['label'] = unicode(te.get_attribute("label"))
            record['value'] = unicode(te.get_attribute("value"))
            record['id'] = unicode(te.get_attribute("id"))
            record['name'] = unicode(te.get_attribute("name"))
            record['aria'] = unicode(te.get_attribute("aria-label"))
            record['maxlen'] = unicode(te.get_attribute("maxlength"))
            record['disabled'] = unicode(te.get_attribute("disabled"))
            record['displayed'] = unicode(te.is_displayed())
            record['enabled'] = unicode(te.is_enabled())
            record['href'] = unicode(te.get_attribute("href"))
            record['autofocus'] = unicode(te.get_attribute("autofocus"))
            record['text'] = unicode(te.text)
            record['string'] = (record['title'].split("\n")[0] + record['type'].split("\n")[0] +
                                record['label'].split("\n")[0] + record['value'].split("\n")[0]).lower()
            record['string'] += (record['id'].split("\n")[0] + record['aria'].split("\n")[0] +
                                 record['name'].split("\n")[0] + record['text'].split("\n")[0]).lower()
            record['key-string'] = "\t " + record['text'].split("\n")[0] + ", \t" + record['name'].split("\n")[0] \
                                   + ", \t" + record['id'].split("\n")[0]
            record['key-string'] += ", \t" + record['aria'].split("\n")[0] + ", \t" + record['label'].split("\n")[0] \
                                    + ", \t" + record['tag']
            record['element'] = te
            return record
        except StaleElementReferenceException:
            return None


def scan_page_for_element(driver, keyword_list, tag_list, exclude_list):
    all_tags, kw_list_len, status = set_union(tag_list), len(keyword_list), [False]*len(keyword_list)
    for tag in all_tags:
        elements = driver.find_elements_by_tag_name(tag)
        try:
            elements.sort(key=lambda x: (x.get_attribute("text"), x.get_attribute("value"), x.get_attribute("title")))
        except StaleElementReferenceException:
            pass
        for index in range(0, kw_list_len):
            if tag not in tag_list[index]:
                continue
            else:
                for e in elements:
                    if False not in status:
                        return status
                    if status[index] is True:
                        break
                    try:
                        if e.tag_name != tag:
                            continue
                    except (StaleElementReferenceException, NoSuchElementException, ElementNotVisibleException):
                        continue
                    exclude_element, element_record = False, get_record(e, tag)
                    if element_record is None:
                        continue
                    if (element_record['displayed'] == unicode(False)) or (element_record['enabled'] == unicode(False)):
                        continue
                    for x in exclude_list[index]:
                        if x in element_record['string']:
                            exclude_element = True
                    if exclude_element is True:
                        continue
                    try:
                        value = element_record['value'].lower().strip().replace(" ", "")
                    except:
                        value = unicode("")
                    try:
                        text = element_record['text'].lower().strip().replace(" ", "")
                    except:
                        text = unicode("")
                    try:
                        type = element_record['type'].lower().strip().replace(" ", "")
                    except:
                        type = unicode("")
                    try:
                        id_ = element_record['id'].lower().strip().replace(" ", "")
                    except:
                        id_ = unicode("")
                    k = keyword_list[index]
                    if (id_ in k) or (text in k) or (value in k) or (type in k):
                        status[index] = True
    return status


def click_closest_match(driver, keywords, tags, exclusions):
    min_length = 100
    keywords.sort()
    for tag in tags:
        elements = driver.find_elements_by_tag_name(tag)
        try:
            elements.sort(key=lambda x: (x.get_attribute("text"), x.get_attribute("value"), x.get_attribute("title")))
        except StaleElementReferenceException:
            pass
        for kw in keywords:
            for e in elements:
                try:
                    if e.tag_name != tag:
                        continue
                except (StaleElementReferenceException, NoSuchElementException):
                    continue
                exclude_element, element_record = False, get_record(e, tag)
                if element_record is None:
                    continue
                if (element_record['displayed'] == unicode(False)) or (element_record['enabled'] == unicode(False)):
                    continue
                for x in exclusions:
                    if x in element_record['string']:
                        exclude_element = True
                if exclude_element is True:
                    continue
                try:
                    value = element_record['value'].lower().strip().replace(" ", "")
                except:
                    value = unicode("")
                try:
                    text = element_record['text'].lower().strip().replace(" ", "")
                except:
                    text = unicode("")
                try:
                    id_ = element_record['id_'].lower().strip().replace(" ", "")
                except:
                    id_ = unicode("")
                if (text == unicode(kw)) or (value == unicode(kw)) or (id_ == unicode(kw)):
                    try:
                        element_record['element'].click()
                        return element_record
                    except (StaleElementReferenceException, ElementNotSelectableException, ElementNotVisibleException):
                        continue
                elif (unicode(kw) in text) or (unicode(kw) in value) or (unicode(kw) in id_):
                    if min_length > len(text):
                        min_record = element_record
                        min_length = len(text)
    if min_length < 100:
        try:
            min_record['element'].click()
        except (StaleElementReferenceException, ElementNotSelectableException, ElementNotVisibleException):
            return None
        return min_record


def scan_page_for_login_status(driver):
    keyword_list = [["password", "pass"], ["signin", "login"], ["next, continue"]]
    tag_list = [["input"], ["input", "a", "button"], ["input", "a", "button"]]
    exclude_list = [["hidden"], ["hidden", "next"], ["hidden"]]
    password_status, login_status, next_status = scan_page_for_element(driver, keyword_list, tag_list, exclude_list)
    return password_status, login_status, next_status


def front_page_login(driver):
    keyword_list, tag_list, exclude_list = [["signin", "login"]], [["input", "a", "button"]], [["hidden", "next"]]
    login_status = scan_page_for_element(driver, keyword_list, tag_list, exclude_list)
    return login_status[0]


def complete_signin(driver, uname, password, clicks):
    print "Regular sign-in page detected..."
    uname_status, clicks = fill_all_uname(driver, uname, clicks)
    print uname_status
    if uname_status is None:
        return -1, clicks
    pwd_status, clicks = fill_all_password(driver, password, clicks)
    print pwd_status
    if pwd_status is None:
        return -1, clicks
    return True, clicks


def google_signin(driver, uname, password, clicks):
    print "I think we found a google style (multi-page) sign-in..."
    uname_status, clicks = fill_all_uname(driver, uname, clicks)
    if uname_status is None:
        return -1, clicks
    c = click_closest_match(driver, ["next"], ["input", "a", "button"], ["hidden"])
    if c is None:
        return -1, clicks
    else:
        clicks.append("click, \t" + c['key-string'])
    pwd_status, clicks = fill_all_password(driver, password, clicks)
    if pwd_status is None:
        return -1, clicks
    return True, clicks


def make_next_move(driver, pw, si, n_, uname, password, clicks):
    print "Password field: ", pw, "\t Sign in field: ", si, "\t Next field: ", n_, "\n"
    # If there is a password field and a sign in button, then fill in the from and hit enter.
    if pw is True:
        return complete_signin(driver, uname, password, clicks)
    # If there is a sign in button, but nothing else. Click it and see what happens next.
    elif (pw is False) and (si is True) and (n_ is False):
        ce = click_closest_match(driver, ["signin", "login"], ["a", "button", "input"], ["hidden"])
        clicks.append("click, \t" + ce['key-string'])
        return False, clicks
    # If there is a next button, but no password field: It's a multi-page sign in form.
    # Fill in what ever you can and then click next.
    elif ((pw is False) and (n_ is True)) or ((clicks[0] == "None") and (pw is False) and (n_ is True)):
        return google_signin(driver, uname, password, clicks)
    else:
        return -1, clicks


def record_login_elements(driver, uname, password):
    print "Recording elements required to login..."
    keywords, tags, exclusions, recorded_clicks = ["signin", "login"], ["a", "button", "input"], ["hidden"], []
    ce = click_closest_match(driver, keywords, tags, exclusions)
    if ce is None:
        recorded_clicks.append("None")
    else:
        recorded_clicks.append("click, \t" + ce['key-string'])
    print recorded_clicks
    login_status, iterations = False, 0
    while (login_status is False) and (iterations <= 5):
        iterations += 1
        page_status = scan_page_for_login_status(driver)
        if len(page_status) != 3:
            login_status = -1
            break
        else:
            password_status, signin_status, next_status = page_status[0], page_status[1], page_status[2]
        login_status, recorded_clicks = make_next_move(driver, password_status, signin_status, next_status, uname,
                                                       password, recorded_clicks)
    if login_status == -1:
        print "Aborting login... Foctor failed you :("
        return None
    else:
        return recorded_clicks


def fill_all_uname(driver, uname, clicks):
    print "Entering username..."
    ret_rec = None
    elements = driver.find_elements_by_tag_name("input")
    keywords = ["email", "user", "name", "id"]
    for e in elements:
        try:
            e.tag_name
        except (StaleElementReferenceException, ElementNotVisibleException, ElementNotSelectableException,
                NoSuchElementException):
            continue
        rec = get_record(e, "input")
        if rec is None:
            continue
        if (rec['enabled'] == unicode(False)) or (rec['displayed'] == unicode(False)):
            continue
        if "hidden" in rec['string']:
            continue
        try:
            value = rec['value'].lower().strip().replace(" ", "")
        except:
            value = unicode("")
        try:
            text = rec['text'].lower().strip().replace(" ", "")
        except:
            text = unicode("")
        try:
            type_ = rec['type'].lower().strip().replace(" ", "")
        except:
            type_ = unicode("")
        try:
            id_ = rec['id'].lower().strip().replace(" ", "")
        except:
            id_ = unicode("")
        try:
            name = rec['name'].lower().strip().replace(" ","")
        except:
            name = unicode("")
        for k in keywords:
            if (k in id_) or (k in type_) or (k in text) or (k in value) or (k in name):
                e.send_keys(uname)
                ret_rec = rec
                clicks.append("username, \t" + ret_rec['key-string'])
                break
    return ret_rec, clicks


def fill_all_password(driver, password, clicks):
    print "Entering password..."
    ret_rec = None
    time.sleep(2)
    elements = driver.find_elements_by_tag_name("input")
    keywords = ["password", "pass"]
    for e in elements:
        rec = get_record(e, "input")
        if (rec is None) or (compare_record(rec, ret_rec) == 1):
            continue
        if (rec['enabled'] == unicode(False)) or (rec['displayed'] == unicode(False)):
            continue
        if "hidden" in rec['string']:
            continue
        try:
            value = rec['value'].lower().strip().replace(" ", "")
        except:
            value = unicode("")
        try:
            text = rec['text'].lower().strip().replace(" ", "")
        except:
            text = unicode("")
        try:
            type_ = rec['type'].lower().strip().replace(" ", "")
        except:
            type_ = unicode("")
        try:
            id_ = rec['id'].lower().strip().replace(" ", "")
        except:
            id_ = unicode("")
        for k in keywords:
            if (k in id_) or (k in type_) or (k in text) or (k in value):
                ret_rec = rec
                e.clear()
                e.send_keys(password)
                e.send_keys(Keys.RETURN)
                clicks.append("password, \t" + rec['key-string'])
                return ret_rec, clicks
    return ret_rec, clicks


def local_timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise LocalTimeoutError(error_message)

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


class LocalTimeoutError(Exception):
    pass


@local_timeout(60)
def find_element_by_record(driver, record):
    incomplete = 0
    if any(c.isalpha() for c in record['id']):
        try:
            print "Getting element with ID: " + record['id']
            e = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, record['id'])))
            return e
        except (StaleElementReferenceException, ElementNotSelectableException, ElementNotVisibleException,
                NoSuchElementException, TimeoutException, LocalTimeoutError):
            incomplete = 1
    if (incomplete == 1) or (record['id'] == "None") or not(any(c.isalpha() for c in record['id'])):
        try:
            print "Getting element with record: ", record
            elements = driver.find_elements_by_tag_name(record['tag'])
        except (StaleElementReferenceException, ElementNotSelectableException, ElementNotVisibleException,
                NoSuchElementException):
            return None
        for e in elements:
            try:
                r = get_record(e, record['tag'])
                if (r['text'].split("\n")[0] == record['text']) and (r['name'].split("\n")[0] == record['name']):
                    return e
            except (StaleElementReferenceException, ElementNotSelectableException, ElementNotVisibleException,
                    NoSuchElementException, TimeoutException, LocalTimeoutError):
                return None
    return None

