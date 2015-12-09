__author__ = 'rishabn'

from foctor_core import *


def read_rule_file(filename, start, stop):
    f = open(filename)
    rules = list()
    for line in f:
        line = line.split(",")
        if (int(line[0]) < int(start)) or (int(line[0]) > int(stop)):
            continue
        if line[2].strip() == "no-matching-rule":
            continue
        rule = dict()
        rule['index'], rule['url'] = line[0].strip(), line[1].strip()
        rule['rule'], rule['name'], rule['id'] = line[2].strip(), line[3].strip(), line[4].strip()
        rules.append(rule)
    return rules


def find_search_rule(driver):
    elements = get_all_input_elements(driver)
    # Rule 1: There is only one input box
    status = single_input_rule(elements)
    if status is True:
        return "single-input"
    # Rule 2: There is only one box with a defined maxlen
    status, length, id_ = single_maxlen_rule(elements)
    if status is True:
        return "single-maxlen, " + str(length) + ", " + str(id_).split("\n")[0]
    # Rule 3: There is only one input element defined to be for "text"
    status, name, id_ = single_textbox_rule(elements)
    if status is True:
        return "single-text-box, " + str(name).split("\n")[0] + ", " + str(id_).split("\n")[0]
    # Rule 4: There is a text box with name "query/querytext/q/search"
    status, name, id_ = text_q_rule(elements)
    if status is True:
        return "text-q, " + str(name).split("\n")[0] + ", " + str(id_).split("\n")[0]
    # Rule 5: There is a non-text element with name "query/querytext/q/search"
    status, name, id_ = non_text_q_rule(elements)
    if status is True:
        return "single-non-text-q, " + str(name).split("\n")[0] + ", " + str(id_).split("\n")[0]
    return "no-matching-rule"


def single_input_rule(elements):
    if len(elements) == 1:
        return True
    return False


def single_maxlen_rule(elements):
    candidates_count, length, id_ = 0, 0, None
    for e in elements:
        if (e['max-length'] is not None) and (unicode("none") not in e['max-length']):
            candidates_count += 1
            length, id_ = e['max-length'], e['id']
    if candidates_count == 1:
        return True, str(length), str(id_)
    return False, "", ""


def single_textbox_rule(elements):
    candidates_count, name, id_ = 0, None, None
    for e in elements:
        if e['type'] == unicode("text"):
            candidates_count += 1
            name, id_ = e['name'], e['id']
    if candidates_count == 1:
        return True, name, id_
    return False, "", ""


def text_q_rule(elements):
    candidates_count, name, id_ = 0, None, None
    keywords = [unicode("q"), unicode("query"), unicode("querytext"), unicode("search")]
    for e in elements:
        if ((e['name'] in keywords) or (e['label'] in keywords) or (e['title'] in keywords)) and (e['type'] == unicode("text")):
            candidates_count += 1
            name, id_ = e['name'], e['id']
    if candidates_count > 0:
        return True, name, id_
    return False, "", ""


def non_text_q_rule(elements):
    candidates_count, name, id_ = 0, None, None
    keywords = [unicode("q"), unicode("query"), unicode("querytext"), unicode("search")]
    for e in elements:
        if (e['name'] in keywords) or (e['label'] in keywords) or (e['title'] in keywords):
            candidates_count += 1
            name, id_ = e['name'], e['id']
    if candidates_count > 0:
        return True, name, id_
    return False, "", ""


def get_all_input_elements(driver):
    all_input_elements = driver.find_elements_by_tag_name("input")
    el_attributes = list()
    for el in all_input_elements:
        attributes = dict()
        attributes['title'] = unicode(el.get_attribute("title"))
        attributes['type'] = unicode(el.get_attribute("type"))
        attributes['label'] = unicode(el.get_attribute("label"))
        attributes['id'] = unicode(el.get_attribute("id"))
        attributes['name'] = unicode(el.get_attribute("name"))
        attributes['aria-label'] = unicode(el.get_attribute("aria-label"))
        attributes['max-length'] = unicode(el.get_attribute("maxlength"))
        attributes['style'] = unicode(el.get_attribute("style"))
        if (attributes not in el_attributes) and (attributes['type'] != "hidden"):
            el_attributes.append(attributes)
    return el_attributes



