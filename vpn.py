#!/usr/bin/python
# Ben Jones bjones99@gatech.edu
# Georgia Tech Fall 2014
#
# vpn.py: a top level interface to commands to run VPNs on a VM as
# different clients. The use case is allowing us to measure from more
# places.

import argparse
import os
import os.path

import centinel.config
import centinel.openvpn


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", nargs=1, dest='directory',
                        help="Directory with experiments, config files, etc.",
                        required=True)
    createConfHelp = ("Create configuration files for the given "
                      "openvpn config files so that we can treat each "
                      "one as a client. The argument should be a "
                      "directory with a subdirectory called openvpn "
                      "that contains the openvpn config files")
    parser.add_argument('--create-config', '-c', help=createConfHelp,
                        nargs=1, dest='createConf')
    return parser.parse_args()


def scan_vpns(config):
    """For each VPN, check if there are experiments and scan with it if
    necessary

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)

    """

    # iterate over each VPN
    vpnDir  = os.path.join(os.path.expanduser(args.directory), "vpns")
    confDir = os.path.join(os.path.expanduser(args.directory), "configs")
    vpn = centinel.openvpn.OpenVPN()
    for filename in os.listdir(confDir):
        vpnConfig = os.path.join(vpnDir, filename)
        centinelConfig = os.path.join(confDir, filename)
        vpn.start(vpnConfig)
        if not vpn.started():
            vpn.stop()
            continue
        # now that the VPN is started, get centinel to process the VPN
        # stuff and sync the results
        configuration = centinel.config.Configuration()
        configuration.parse_config(centinelConfig)
        client = centinel.client.Client(configuration.params)
        client.setup_logging()
        client.run()
        centinel.backend.sync(configuration.params)


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
    vpnDir  = os.path.join(os.path.expanduser(directory), "vpns")
    confDir = os.path.join(os.path.expanduser(directory), "configs")
    homeDirs = os.path.join(os.path.expanduser(directory), "home")
    for filename in os.listdir(vpnDir):
        configuration = centinel.config.Configuration()
        # setup the directories
        homeDir = os.path.join(homeDirs, filename)
        os.mkdir(homeDir)
        configuration.params['dirs']['centinel_home'] = homeDir
        expDir = os.path.join(homeDir, "experiments")
        os.mkdir(expDir)
        configuration.params['dirs']['experiments_dir'] = expDir
        dataDir = os.path.join(homeDir, "data")
        os.mkdir(dataDir)
        configuration.params['dirs']['data_dir'] = dataDir
        resDir = os.path.join(homeDir, "results")
        os.mkdir(resDir)
        configuration.params['dirs']['results_dir'] = resDir

        logFile = os.path.join(homeDir, "centinel.log")
        configuration.params['log']['log_file'] = logFile
        loginFile = os.path.join(homeDir, "login")
        configuration.params['server']['login_file'] = loginFile

        confFile = os.path.join(confDir, filename)
        configuration.write_out_config(confFile)


if __name__ == "__main__":
    args = parse_args()

    if args.createConf:
        # create the config files for the openvpn config files
        create_config_files(args.createConf)

    scan_vpns(args.directory)
