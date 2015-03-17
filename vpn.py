#!/usr/bin/python
# vpn.py: a top level interface to commands to run VPNs on a VM as
# different clients. The use case is allowing us to measure from more
# places.

import argparse
import logging
import os

import centinel.backend
import centinel.client
import centinel.config
import centinel.vpn.openvpn as openvpn
import centinel.vpn.hma as hma


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auth-file', '-u', dest='auth_file', default=None,
                        help=("File with HMA username on first line, \n"
                              "HMA password on second line"))
    parser.add_argument('--create-hma-configs', dest='create_HMA',
                        action="store_true",
                        help='Create the openvpn config files for HMA')
    parser.add_argument('--exclude', "-e", dest='exclude_list', default=None,
                        help=('Countries to exclude when scanning (comma '
                              'separated two letter country codes)'))
    parser.add_argument('--log-file', '-l', dest='log_file', default=None,
                        help="Log file location")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--directory", "-d", dest='directory',
                       help="Directory with experiments, config files, etc.")
    create_conf_help = ("Create configuration files for the given "
                        "openvpn config files so that we can treat each "
                        "one as a client. The argument should be a "
                        "directory with a subdirectory called openvpn "
                        "that contains the openvpn config files")
    group.add_argument('--create-config', '-c', help=create_conf_help,
                       dest='create_conf_dir')
    return parser.parse_args()


def scan_vpns(directory, auth_file, exclude_list):
    """For each VPN, check if there are experiments and scan with it if
    necessary

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)

    """

    logging.info("Starting to run the experiments for each VPN")
    logging.warn("Excluding vantage points from: %s" % (exclude_list))

    # iterate over each VPN
    vpn_dir = return_abs_path(directory, "vpns")
    conf_dir = return_abs_path(directory, "configs")
    auth_file = return_abs_path(".", auth_file)
    for filename in os.listdir(conf_dir):
        logging.info("Moving onto %s" % (filename))
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
        vpn_address, extension = os.path.splitext(filename)
        country = None
        try:
            geo = centinel.backend.geolocate(config.params,
                                             vpn_address)
            if 'country' in geo:
                country = geo['country']
        except Exception as exp:
            logging.error("%s: Failed to geolocate "
                          "%s: %s" % (filename, vpn_address, exp))

        if country and exclude_list and country in exclude_list:
            logging.info("%s: Skipping this server (%s)" % (filename, country))
            continue

        # try setting the VPN info (IP and country) to get appropriate
        # experiemnts and input data.
        try:
            centinel.backend.set_vpn_info(config.params, vpn_address, country)
        except Exception as exp:
            logging.error("%s: Failed to set VPN info: %s" % (filename, exp))

        if not centinel.backend.experiments_available(config.params):
            logging.info("%s: No experiments available." % (filename))
            continue

        logging.info("%s: Synchronizing." % (filename))
        try:
            centinel.backend.sync(config.params)
        except Exception as exp:
            logging.error("%s: Failed to sync: %s" % (filename, exp))

        logging.info("%s: Starting VPN." % (filename))
        vpn = openvpn.OpenVPN(timeout=30, auth_file=auth_file,
                                       config_file=vpn_config)
        vpn.start()
        if not vpn.started:
            vpn.stop()
            logging.error("%s: Failed to start VPN!" % (filename))
            continue

        logging.info("%s: Running Centinel." % (filename))
        try:
            client = centinel.client.Client(config.params)
            client.setup_logging()
            client.run()
        except Exception as exp:
            logging.error("%s: Error running Centinel: %s" % (filename, exp))

        logging.info("%s: Stopping VPN." % (filename))
        vpn.stop()

        logging.info("%s: Synchronizing." % (filename))
        try:
            centinel.backend.sync(config.params)
        except Exception as exp:
            logging.error("%s: Failed to sync: %s" % (filename, exp))

        # try setting the VPN info (IP and country) to the correct address
        # after sync is over.
        try:
            centinel.backend.set_vpn_info(config.params, vpn_address, country)
        except Exception as exp:
            logging.error("Failed to set VPN info: %s" % (exp))

def return_abs_path(directory, path):
    """Unfortunately, Python is not smart enough to return an absolute
    path with tilde expansion, so I writing functionality to do this

    """
    if directory is None or path is None:
        return
    directory = os.path.expanduser(directory)
    return os.path.abspath(os.path.join(directory, path))

def create_config_files(directory):

    """For each VPN file in directory/vpns, create a new configuration
    file and all the associated directories

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)
    -----results (contains the results)

    """
    logging.info("Starting to create config files from openvpn files")

    vpn_dir = return_abs_path(directory, "vpns")
    conf_dir = return_abs_path(directory, "configs")
    os.mkdir(conf_dir)
    home_dirs = return_abs_path(directory, "home")
    os.mkdir(home_dirs)
    for filename in os.listdir(vpn_dir):
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

        conf_file = os.path.join(conf_dir, filename)
        configuration.write_out_config(conf_file)


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(filename=args.log_file,
                        format="%(levelname)s %(asctime)s: %(message)s",
                        level=logging.INFO)
    if args.create_conf_dir:
        if args.create_HMA:
            hmaDir = return_abs_path(args.create_conf_dir, "vpns")
            hma.create_config_files(hmaDir)
        # create the config files for the openvpn config files
        create_config_files(args.create_conf_dir)
    else:
        scan_vpns(args.directory, args.auth_file, args.exclude_list)
