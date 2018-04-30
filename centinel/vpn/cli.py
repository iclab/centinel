#!/usr/bin/python
# vpn.py: a top level interface to commands to run VPNs on a VM as
# different clients. The use case is allowing us to measure from more
# places.

import argparse
import logging
from random import shuffle
import os
import time
import sys
import signal
import dns.resolver
import json
import socket
import shutil

import centinel.backend
import centinel.client
import centinel.config
import centinel.vpn.openvpn as openvpn
import centinel.vpn.hma as hma
import centinel.vpn.ipvanish as ipvanish
import centinel.vpn.purevpn as purevpn
import centinel.vpn.vpngate as vpngate

import country_module as convertor
import probe as probe
import geosanity as san

PID_FILE = "/tmp/centinel.lock"
log_file = 'log_vpn.log'
logging.basicConfig(format="%(asctime)s %(filename)s:%(lineno)d %(levelname)s: %(message)s",
                    filename=log_file)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auth-file', '-u', dest='auth_file', default=None,
                        help=("File with HMA username on first line, \n"
                              "HMA password on second line"))
    parser.add_argument('--crt-file', '-r', dest='crt_file', default=None,
                        help=("Certificate file for the current vpn\n"
                              "provider, if provided"))
    parser.add_argument('--tls-auth', '-t', dest='tls_auth', default=None,
                        help="Key for additional layer of authentication")
    parser.add_argument('--key-direction', '-k', dest='key_direction', default=None,
                        help=("Key direction for tls auth, must specify when "
                              "tls-auth is used"))
    parser.add_argument('--geo-sanity-check', dest='sanity_check',
                        action="store_true", default=False,
                        help=("Run sanity check module to remove lying VP servers "
                              "from our vantage point list"))
    parser.add_argument('--reduce-endpoint', dest='reduce_vp',
                        action="store_true", default=False,
                        help="Reduce the number of vantage points by only connect to "
                             "one vantage point for each AS and country combination")
    g1 = parser.add_mutually_exclusive_group()
    g1.add_argument('--create-hma-configs', dest='create_HMA',
                    action="store_true",
                    help='Create the openvpn config files for HMA')
    g1.add_argument('--update-hma-configs', dest='update_HMA',
                    action="store_true",
                    help='Update the openvpn config files for HMA')
    g1.add_argument('--create-ipvanish-configs', dest='create_IPVANISH',
                    action='store_true',
                    help='Create the openvpn config files for IPVanish')
    g1.add_argument('--update-ipvanish-configs', dest='update_IPVANISH',
                    action="store_true",
                    help='Update the openvpn config files for IPVANISH')
    g1.add_argument('--create-purevpn-configs', dest='create_PUREVPN',
                    action='store_true',
                    help='Create the openvpn config files for PureVPN')
    g1.add_argument('--create-vpngate-configs', dest='create_VPNGATE',
                    action='store_true',
                    help='Create the openvpn config files for VPN Gate')
    g1.add_argument('--update-purevpn-configs', dest='update_PUREVPN',
                    action="store_true",
                    help='Update the openvpn config files for PUREVPN')
    parser.add_argument('--shuffle', '-s', dest='shuffle_lists',
                        action="store_true", default=False,
                        help='Randomize the order of vantage points')
    parser.add_argument('--exclude', '-e', dest='exclude_list', default=None,
                        help=('Countries to exclude when scanning (comma '
                              'separated two letter country codes)'))
    parser.add_argument('--log-file', '-l', dest='log_file', default=None,
                        help="Log file location")
    g2 = parser.add_mutually_exclusive_group(required=True)
    g2.add_argument('--directory', '-d', dest='directory',
                    help='Directory with experiments, config files, etc.')
    create_conf_help = ('Create/Update configuration files for the given '
                        'openvpn config files so that we can treat each '
                        'one as a client. The argument should be a '
                        'directory with a subdirectory called openvpn '
                        'that contains the openvpn config files')
    g2.add_argument('--create-config', '-c', help=create_conf_help,
                    dest='create_conf_dir')

    g2.add_argument('--update-config', '-z', help=create_conf_help,
                    dest='update_conf_dir')

    # following args are used to support splitting clients among multiple VMs
    # each running vpn walker will use this to decide which portion of vpn
    # endpoints it should include
    parser.add_argument('--vm-num', dest='vm_num', type=int, default=1,
                        help="Specify the number of VMs running concurrently")
    parser.add_argument('--vm-index', dest='vm_index', type=int, default=1,
                        help='The index of current VM, must be >= 1 and '
                             '<= vm_num')
    return parser.parse_args()


def scan_vpns(directory, auth_file, crt_file, tls_auth, key_direction,
              exclude_list, shuffle_lists, vm_num, vm_index, reduce_vp, sanity_check):
    """
    For each VPN, check if there are experiments and scan with it if
    necessary

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)

    :param directory: root directory that contains vpn configs and
                      centinel client configs
    :param auth_file: a text file with username at first line and
                      password at second line
    :param crt_file: optional root certificate file
    :param tls_auth: additional key
    :param key_direction: must specify if tls_auth is used
    :param exclude_list: optional list of exluded countries
    :param shuffle_lists: shuffle vpn list if set true
    :param vm_num: number of VMs that are running currently
    :param vm_index: index of current VM
    :param reduce_vp: reduce number of vantage points
    :return:
    """

    logging.info("Starting to run the experiments for each VPN")
    logging.warn("Excluding vantage points from: %s" % exclude_list)

    # iterate over each VPN
    vpn_dir = return_abs_path(directory, "vpns")
    conf_dir = return_abs_path(directory, "configs")
    home_dir = return_abs_path(directory, "home")
    if auth_file is not None:
        auth_file = return_abs_path(directory, auth_file)
    if crt_file is not None:
        crt_file = return_abs_path(directory, crt_file)
    if tls_auth is not None:
        tls_auth = return_abs_path(directory, tls_auth)
    conf_list = sorted(os.listdir(conf_dir))

    # determine VPN provider
    vpn_provider = None
    if "hma" in directory:
        vpn_provider = "hma"
    elif "ipvanish" in directory:
        vpn_provider = "ipvanish"
    elif "purevpn" in directory:
        vpn_provider = "purevpn"
    elif "vpngate" in directory:
        vpn_provider = "vpngate"
    if vpn_provider:
        logging.info("Detected VPN provider is %s" % vpn_provider)
    else:
        logging.warning("Cannot determine VPN provider!")

    # geolocation sanity check
    if sanity_check:
        start_time = time.time()
        sanity_path = os.path.join(directory, '../sanitycheck')
        if not os.path.exists(sanity_path):
            os.makedirs(sanity_path)
        anchors = probe.retrieve_anchor_list(sanity_path)
        logging.info("Anchors list fetched")
        # send pings
        probe.start_probe(conf_list, conf_dir, vpn_dir, auth_file, crt_file, tls_auth,
                key_direction, sanity_path, vpn_provider, anchors)
        # sanity check
        new_conf_list = san.start_sanity_check(sanity_path, vpn_provider, anchors)
        logging.info("List size after sanity check. New size: %d" % len(new_conf_list))
        conf_list = new_conf_list
        end_time = time.time() - start_time
        logging.info("Finished sanity check: total elapsed time (%.2f)" %end_time)

    # reduce size of list if reduce_vp is true
    if reduce_vp:
        logging.info("Reducing list size. Original size: %d" % len(conf_list))
        country_asn_set = set()
        reduced_conf_set = set()
        for filename in conf_list:
            centinel_config = os.path.join(conf_dir, filename)
            config = centinel.config.Configuration()
            config.parse_config(centinel_config)
            hostname = os.path.splitext(filename)[0]
            try:
                vp_ip = socket.gethostbyname(hostname)
            except Exception as exp:
                logging.exception("Failed to resolve %s : %s" %(hostname, str(exp)))
                continue
            # get country for this vpn
            with open(centinel_config) as fc:
                json_data = json.load(fc)
            country_in_config = ""
            if 'country' in json_data:
                country_in_config = json_data['country']

            try:
                meta = centinel.backend.get_meta(config.params, vp_ip)
                # send country name to be converted to alpha2 code
                if (len(country_in_config) > 2):
                    meta['country'] = convertor.country_to_a2(country_in_config)
                if 'country' in meta and 'as_number' in meta \
                        and meta['country'] and meta['as_number']:
                    country_asn = '_'.join([meta['country'], meta['as_number']])
                    if country_asn not in country_asn_set:
                        country_asn_set.add(country_asn)
                        reduced_conf_set.add(filename)
                else:
                    # run this endpoint if missing info
                    reduced_conf_set.add(filename)
            except:
                logging.warning("Failed to geolocate %s" % vp_ip)
                reduced_conf_set.add(filename)

        conf_list = list(reduced_conf_set)
        logging.info("List size reduced. New size: %d" % len(conf_list))

    # sort file list to ensure the same filename sequence in each VM
    conf_list = sorted(conf_list)

    # only select its own portion according to vm_num and vm_index
    chunk_size = len(conf_list) / vm_num
    last_chunk_additional = len(conf_list) % vm_num
    start_pointer = 0 + (vm_index - 1) * chunk_size
    end_pointer = start_pointer + chunk_size
    if vm_index == vm_num:
        end_pointer += last_chunk_additional
    conf_list = conf_list[start_pointer:end_pointer]

    if shuffle_lists:
        shuffle(conf_list)

    number = 1
    total = len(conf_list)

    external_ip = get_external_ip()
    if external_ip is None:
        logging.error("No network connection, exiting...")
        return
    logging.info("Current external IP: %s" % (external_ip))

    # getting namesevers that should be excluded
    local_nameservers = dns.resolver.Resolver().nameservers

    for filename in conf_list:
        # Check network connection first
        time.sleep(5)
        logging.info("Checking network connectivity...")
        current_ip = get_external_ip()
        if current_ip is None:
            logging.error("Network connection lost!")
            break
        elif current_ip != external_ip:
            logging.error("VPN still connected! IP: %s" % current_ip)
            if len(openvpn.OpenVPN.connected_instances) == 0:
                logging.error("No active OpenVPN instance found! Exiting...")
                break
            else:
                logging.warn("Trying to disconnect VPN")
                for instance in openvpn.OpenVPN.connected_instances:
                    instance.stop()
                    time.sleep(5)

                current_ip = get_external_ip()
                if current_ip is None or current_ip != external_ip:
                    logging.error("Stopping VPN failed! Exiting...")
                    break

            logging.info("Disconnecting VPN successfully")

        # start centinel for this endpoint
        logging.info("Moving onto (%d/%d) %s" % (number, total, filename))

        number += 1
        vpn_config = os.path.join(vpn_dir, filename)
        centinel_config = os.path.join(conf_dir, filename)

        # before starting the VPN, check if there are any experiments
        # to run
        config = centinel.config.Configuration()
        config.parse_config(centinel_config)

        # assuming that each VPN config file has a name like:
        # [ip-address].ovpn, we can extract IP address from filename
        # and use it to geolocate and fetch experiments before connecting
        # to VPN.
        #  filename is [OBhostname].ovpn, we resolved the hostname to ip
        #  using socket.gethostbyname()
        hostname = os.path.splitext(filename)[0]
        vp_ip = "unknown"
        try:
            vp_ip = socket.gethostbyname(hostname)
        except Exception as exp:
            logging.exception("Failed to resolve %s : %s" %(hostname, str(exp)))
            continue

        # vpn_address, extension = os.path.splitext(filename)
        lines = [line.rstrip('\n') for line in open(centinel_config)]

        # get country for this vpn
        country_in_config = ""
        # reading the server.txt file in vpns folder
        for line in lines:
            if "country" in line:
                (key, country_in_config) = line.split(': ')
                country_in_config = country_in_config.replace('\"', '').replace(',', '')

        country = None
        try:
            # we still might need some info from the Maximind query
            meta = centinel.backend.get_meta(config.params, vp_ip)

            # send country name to be converted to alpha2 code
            if (len(country_in_config) > 2):
                meta['country'] = convertor.country_to_a2(country_in_config)
            # some vpn config files already contain the alpha2 code (length == 2)
            if 'country' in meta:
                country = meta['country']
        except:
            logging.exception("%s: Failed to geolocate %s" % (filename, vp_ip))

        if country and exclude_list and country in exclude_list:
            logging.info("%s: Skipping this server (%s)" % (filename, country))
            continue

        # try setting the VPN info (IP and country) to get appropriate
        # experiemnts and input data.
        try:
            logging.info("country is %s" % country)
            centinel.backend.set_vpn_info(config.params, vp_ip, country)
        except Exception as exp:
            logging.exception("%s: Failed to set VPN info: %s" % (filename, exp))

        logging.info("%s: Synchronizing." % filename)
        try:
            centinel.backend.sync(config.params)
        except Exception as exp:
            logging.exception("%s: Failed to sync: %s" % (filename, exp))

        if not experiments_available(config.params):
            logging.info("%s: No experiments available." % filename)
            try:
                centinel.backend.set_vpn_info(config.params, vp_ip, country)
            except Exception as exp:
                logging.exception("Failed to set VPN info: %s" % exp)
            continue

        # add exclude_nameservers to scheduler
        sched_path = os.path.join(home_dir, filename, "experiments", "scheduler.info")
        if os.path.exists(sched_path):
            with open(sched_path, 'r+') as f:
                sched_info = json.load(f)
                for task in sched_info:
                    if "python_exps" in sched_info[task] and "baseline" in sched_info[task]["python_exps"]:
                        if "params" in sched_info[task]["python_exps"]["baseline"]:
                            sched_info[task]["python_exps"]["baseline"]["params"]["exclude_nameservers"] = \
                                local_nameservers
                        else:
                            sched_info[task]["python_exps"]["baseline"]["params"] = \
                                {"exclude_nameservers": local_nameservers}

                # write back to same file
                f.seek(0)
                json.dump(sched_info, f, indent=2)
                f.truncate()

        # before starting the vpn do the sanity check
        # create a directory to store the RIPE anchor list and landmarks_list in it so other vpns could use it as well
        # sanity_path = os.path.join(directory,'../sanitycheck')
        # if not os.path.exists(sanity_path):
        #    os.makedirs(sanity_path)

        # fetch the list of RIPE anchors
        # anchors = probe.get_anchor_list(sanity_path)

        # logging.info("Anchors list fetched")
        logging.info("%s: Starting VPN." % filename)

        vpn = openvpn.OpenVPN(timeout=60, auth_file=auth_file, config_file=vpn_config,
                              crt_file=crt_file, tls_auth=tls_auth, key_direction=key_direction)

        vpn.start()
        if not vpn.started:
            logging.error("%s: Failed to start VPN!" % filename)
            vpn.stop()
            time.sleep(5)
            continue


            # sending ping to the anchors
        # ping_result = probe.perform_probe(sanity_path, vpn_provider,vpn_provider,country,anchors)

        # have to do this sanity check if timestamp is a certain value, needs changing
        # timestamp = time.time()
        # ping_result['timestamp'] = timestamp



        logging.info("%s: Running Centinel." % filename)
        try:
            client = centinel.client.Client(config.params, vpn_provider)
            centinel.conf = config.params
            # do not use client logging config
            # client.setup_logging()
            client.run()
        except Exception as exp:
            logging.exception("%s: Error running Centinel: %s" % (filename, exp))

        logging.info("%s: Stopping VPN." % filename)
        vpn.stop()
        time.sleep(5)

        logging.info("%s: Synchronizing." % filename)
        try:
            centinel.backend.sync(config.params)
        except Exception as exp:
            logging.exception("%s: Failed to sync: %s" % (filename, exp))

        # try setting the VPN info (IP and country) to the correct address
        # after sync is over.
        try:
            centinel.backend.set_vpn_info(config.params, vp_ip, country)
        except Exception as exp:
            logging.exception("Failed to set VPN info: %s" % exp)


def return_abs_path(directory, path):
    """
    Unfortunately, Python is not smart enough to return an absolute
    path with tilde expansion, so I writing functionality to do this

    :param directory:
    :param path:
    :return:
    """
    if directory is None or path is None:
        return
    directory = os.path.expanduser(directory)
    return os.path.abspath(os.path.join(directory, path))


def get_external_ip():
    # pool of URLs that returns public IP
    url_list = ["https://wtfismyip.com/text",
                "http://ip.42.pl/raw",
                "http://myexternalip.com/raw",
                "https://api.ipify.org/"]

    from urllib2 import urlopen, URLError
    # try four urls in case some are unreachable
    for url in url_list:
        try:
            my_ip = urlopen(url, timeout=5).read().rstrip()
            return my_ip
        except URLError:
            logging.warning("Failed to connect to %s" % url)
            continue
    # return None if all failed
    return None


def signal_handler(signal, frame):
    logging.warn("SIGINT or SIGTERM received")
    if len(openvpn.OpenVPN.connected_instances) > 0:
        logging.warn("Disconnecting VPN")
        for instance in openvpn.OpenVPN.connected_instances:
            instance.stop()
    sys.exit(0)


def update_config_files(directory, vp_list):
    """
    For each VPN file in directory/vpns update its configuration if needed
    :param directory:
    :param vp_list: the list of vp updates/deletes/additions
    :return:
    """

    logging.info("Starting to update config files")
    server_country = {}
    vpn_dir = return_abs_path(directory, "vpns")
    print(vpn_dir)
    new_vpn_dir = return_abs_path(directory, "updated_vpns")

    # read servers.txt to find the country associated with the ip
    with open(vpn_dir + '/servers.txt') as server_file:
        servers = server_file.readlines()

    for server_line in servers:
        server_line = (server_line.split('|'))
        server_country[server_line[0]] = server_line[1].replace('\n', '')

    conf_dir = return_abs_path(directory, "configs")
    home_dirs = return_abs_path(directory, "home")

    # remove vps
    for vp in vp_list[0]:
        os.remove(os.path.join(directory, "vpns/" + vp))
        shutil.rmtree(os.path.join(directory, "home/" + vp))
        os.remove(os.path.join(directory, "configs/" + vp))

    # update vps
    for vp in vp_list[1]:
        print('in update')
        os.remove(os.path.join(directory, "vpns/" + vp))
        shutil.copyfile(os.path.join(directory, "updated_vpns/" + vp), os.path.join(directory, "vpns/" + vp))
    # add vp
    for vp in vp_list[2]:
        print(os.path.join(directory, "vpns/" + vp))
        shutil.copyfile(os.path.join(directory, "updated_vpns/" + vp), os.path.join(directory, "vpns/" + vp))
        configuration = centinel.config.Configuration()
        # setup the directories
        home_dir = os.path.join(home_dirs, vp)
        os.mkdir(home_dir)
        configuration.params['user']['centinel_home'] = home_dir
        exp_dir = os.path.join(home_dir, "experiments")
        os.mkdir(exp_dir)
        configuration.params['dirs']['experiments_dir'] = exp_dir
        data_dir = os.path.join(home_dir, "data")
        os.mkdir(data_dir)
        configuration.params['dirs']['data_dir'] = data_dir
        res_dir = os.path.join(home_dir, "results")
        os.mkdir(res_dir)
        configuration.params['dirs']['results_dir'] = res_dir

        log_file = os.path.join(home_dir, "centinel.log")
        configuration.params['log']['log_file'] = log_file
        login_file = os.path.join(home_dir, "login")
        configuration.params['server']['login_file'] = login_file
        configuration.params['user']['is_vpn'] = True

        configuration.params['server']['verify'] = True
        configuration.params['experiments']['tcpdump_params'] = ["-i", "tun0"]
        configuration.params['country'] = server_country[vp.replace('.ovpn', '')]
        conf_file = os.path.join(conf_dir, vp)
        configuration.write_out_config(conf_file)
    shutil.rmtree(new_vpn_dir)


def create_config_files(directory, provider):
    """
    For each VPN file in directory/vpns, create a new configuration
    file and all the associated directories

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)
    -----results (contains the results)

    :param directory:
    """
    logging.info("Starting to create config files from openvpn files")
    server_country = {}
    vpn_dir = return_abs_path(directory, "vpns")

    # read servers.txt to find the country associated with the ip
    with open(vpn_dir + '/servers.txt') as server_file:
        servers = server_file.readlines()

    for server_line in servers:
        server_line = (server_line.split('|'))
        server_country[server_line[0]] = server_line[1].replace('\n', '')

    conf_dir = return_abs_path(directory, "configs")
    os.mkdir(conf_dir)
    home_dirs = return_abs_path(directory, "home")
    os.mkdir(home_dirs)
    for filename in os.listdir(vpn_dir):
        if ('servers' not in filename):
            configuration = centinel.config.Configuration()
            # setup the directories
            home_dir = os.path.join(home_dirs, filename)
            os.mkdir(home_dir)
            configuration.params['user']['centinel_home'] = home_dir
            exp_dir = os.path.join(home_dir, "experiments")
            os.mkdir(exp_dir)
            configuration.params['dirs']['experiments_dir'] = exp_dir
            data_dir = os.path.join(home_dir, "data")
            os.mkdir(data_dir)
            configuration.params['dirs']['data_dir'] = data_dir
            res_dir = os.path.join(home_dir, "results")
            os.mkdir(res_dir)
            configuration.params['dirs']['results_dir'] = res_dir

            log_file = os.path.join(home_dir, "centinel.log")
            configuration.params['log']['log_file'] = log_file
            login_file = os.path.join(home_dir, "login")
            configuration.params['server']['login_file'] = login_file
            configuration.params['user']['is_vpn'] = True

            configuration.params['server']['verify'] = True
            configuration.params['experiments']['tcpdump_params'] = ["-i", "tun0"]
            configuration.params['country'] = server_country[filename.replace('.ovpn', '')]
            hostname = os.path.splitext(filename)[0]
            vp_ip = "unknown"
            try:
                vp_ip = socket.gethostbyname(hostname)
            except Exception as exp:
                logging.exception("Failed to resolve %s : %s" % (hostname, str(exp)))
            configuration.params['custom_meta']['provider'] = provider
            configuration.params['custom_meta']['hostname'] = hostname
            configuration.params['custom_meta']['ip_address'] = vp_ip
            conf_file = os.path.join(conf_dir, filename)
            configuration.write_out_config(conf_file)


def experiments_available(config):
    logging.info("Starting to check for experiments with %s",
                 config['server']['server_url'])
    try:
        client = centinel.client.Client(config)
        if client.has_experiments_to_run():
            return True
    except Exception, exp:
        logging.exception("Unable to check schedule: %s", str(exp))

    return False


def run():
    if os.path.isfile(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read()
            print "Centinel already running (PID = %s)" % pid
            print "Lock file address: %s" % PID_FILE
        sys.exit(1)

    try:
        f = open(PID_FILE, "w")
        f.write("%d" % os.getpid())
        f.close()
    except Exception as exp:
        sys.stderr.write('Error to writing the'
                         ' lock file: %s\n' % exp)
        sys.exit(1)

    try:
        _run()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print "Keyboard interrupt received, exiting..."
    except Exception as exp:
        sys.stderr.write("%s" % exp)

    try:
        os.remove(PID_FILE)
    except Exception as exp:
        sys.stderr.write("Failed to remove lock file %s: %s" % (PID_FILE, exp))


def _run():
    """Entry point for all uses of centinel"""
    args = parse_args()

    # register signal handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # set up logging
    log_formatter = logging.Formatter("%(asctime)s %(filename)s(line %(lineno)d) "
                                      "%(levelname)s: %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # add file handler if specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)

    # check vm_num and vm_index value
    if args.vm_num < 1:
        print "vm_num value cannot be negative!"
        return
    if args.vm_index < 1 or args.vm_index > args.vm_num:
        print "vm_index value cannot be negative or greater than vm_num!"
        return
    provider = "None"
    if args.create_conf_dir:
        if args.create_HMA:
            hma_dir = return_abs_path(args.create_conf_dir, 'vpns')
            provider = 'hma'
            hma.create_config_files(hma_dir)
        elif args.create_IPVANISH:
            ipvanish_dir = return_abs_path(args.create_conf_dir, 'vpns')
            provider = 'ipvanish'
            ipvanish.create_config_files(ipvanish_dir)
        elif args.create_PUREVPN:
            purevpn_dir = return_abs_path(args.create_conf_dir, 'vpns')
            provider = 'purevpn'
            purevpn.create_config_files(purevpn_dir)
        elif args.create_VPNGATE:
            vpngate_dir = return_abs_path(args.create_conf_dir, 'vpns')
            provider = 'vpngate'
            vpngate.create_config_files(vpngate_dir)
        # create the config files for the openvpn config files
        create_config_files(args.create_conf_dir, provider)

    elif args.update_conf_dir:
        if args.update_HMA:
            hma_dir = return_abs_path(args.update_conf_dir, 'vpns')
            provider = 'hma'
            vp_list = hma.update_config_files(hma_dir)
        if args.update_IPVANISH:
            ipvanish_dir = return_abs_path(args.update_conf_dir, 'vpns')
            provdier = 'ipvanish'
            vp_list = ipvanish.update_config_files(ipvanish_dir)
        if args.update_PUREVPN:
            purevpn_dir = return_abs_path(args.update_conf_dir, 'vpns')
            provider = 'purevpn'
            vp_list = purevpn.update_config_files(purevpn_dir)
        update_config_files(args.update_conf_dir, vp_list)

        # add new ones

    else:
        # sanity check tls_auth and key_direction
        if (args.tls_auth is not None and args.key_direction is None) or \
                (args.tls_auth is None and args.key_direction is not None):
            logging.error("tls_auth and key_direction must be specified "
                          "together!")
            return

        scan_vpns(directory=args.directory, auth_file=args.auth_file,
                  crt_file=args.crt_file, tls_auth=args.tls_auth,
                  key_direction=args.key_direction, exclude_list=args.exclude_list,
                  shuffle_lists=args.shuffle_lists, vm_num=args.vm_num,
                  vm_index=args.vm_index, reduce_vp=args.reduce_vp,
                  sanity_check=args.sanity_check)


if __name__ == "__main__":
    run()
