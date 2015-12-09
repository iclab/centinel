__author__ = 'rishabn'

import os
import time


def copy_file(source, destination):
    command = "sudo cp " + source + " " + destination
    os.system(command)


def kill_list_of_programs(programs):
    for i in programs:
        command = "sudo pkill --signal 9 " + i
        os.system(command)


def start_program(path, delay=45):
    os.system(path + " &")
    time.sleep(delay)
    return path


def start_tcpdump(params, filename):
    command = "sudo tcpdump" + params + filename + " &"
    os.system(command)
    time.sleep(1)


def stop_tcpdump():
    command = "sudo pkill tcpdump"
    os.system(command)
    time.sleep(1)


def make_folder(path):
    try:
        command = "mkdir -p " + path
        if os.path.exists(path) is False:
            os.system(command)
    except Exception as e:
        pass


def delete_content(fd):
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)


def uniquify(l):
    ul = [list(x) for x in set(tuple(x) for x in l)]
    return ul


def set_union(list_of_lists):
    l_l = list_of_lists
    union = list()
    for l in l_l:
        set_l = set(l)
        for item in set_l:
            union.append(item)
    return set(union)


def create_tor_config(port, torrc_name, exits):
    torrc_str = "UseEntryGuards 1\n"
    torrc_str += "SocksPort " + port + "\n"
    if exits != "ALL":
        if len(exits) == 2:
            torrc_str += "ExitNodes {" + exits + "}\n"
        else:
            torrc_str += "ExitNodes " + exits + "\n"
    torrc_str += "StrictNodes 1\n"
    make_folder("./tor-dd-" + port)
    torrc_str += "DataDirectory ./tor-dd-" + port + "/\n"
    conf = open(torrc_name, "w")
    conf.write(torrc_str)
    conf.close()
    return torrc_name
