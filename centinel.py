#!/usr/bin/env python
import sys
import argparse
import getpass
import os

import centinel
import centinel.config

# Constants
DEFAULT_CONFIG_FILE = os.path.expanduser('~' + getpass.getuser() +
                                         "/.centinel/config.ini")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='Configuration file',
                        dest='config')
    no_verify_help = ("Disable certificate verification (NOT RECOMMENDED! "
                      "Use only when debugging.)")
    parser.add_argument('--no_verify', '-nv', help=no_verify_help,
                        action='store_true')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--version', '-v', action='version',
                       version="Centinel %s" % (centinel.__version__),
                       help='Sync data with server')
    group.add_argument('--sync', help='Sync data with server',
                       action='store_true')
    consent_help = ("Give informed consent so that you can download "
                    "experiments from the researchers at ICLab and upload "
                    "results for analysis")
    group.add_argument('--informed-consent', help=consent_help,
                       dest='consent', default=False, action='store_true')

    daemon_help = ('Create cron jobs to run centinel in the background and '
                   'autoupdate. You must be root to use this functionality')
    daemon_parser = subparsers.add_parser('daemonize', help=daemon_help)
        binary_help = ('Name or location of the binary to use in the cron job '
                   'for centinel')
    daemon_parser.add_argument('--binary', default=None, help=binary_help)
    update_help = ('Create an autoupdate script for the installed package. '
                   'Note that you must have installed from a pip package for '
                   'this to work correctly')
    daemon_parser.add_argument('--auto-update', action='store_true',
                               help=update_help)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # we need to store some persistent info, so check if a config file
    # exists (default location is ~/.centinel/config.ini). If the file
    # does not exist, then create a new one at run time
    configuration = centinel.config.Configuration()
    if args.config:
        configuration.parse_config(args.config)
    else:
        # if the file does not exist, then the default config file
        # will be used
        if os.path.exists(DEFAULT_CONFIG_FILE):
            configuration.parse_config(DEFAULT_CONFIG_FILE)
        else:
            configuration.write_out_config(DEFAULT_CONFIG_FILE)

    client = centinel.client.Client(configuration.params)
    client.setup_logging()

    # disable cert verification if the flag is set
    if args.no_verify:
        configuration.params['server']['cert_bundle'] = False

    user = centinel.backend.User(configuration.params)
    # Note: because we have mutually exclusive arguments, we don't
    # have to worry about multiple arguments being called
    if args.sub_command == 'daemonize':
        print "here"
        package_info = configs.params.get('package')
        package_name = None
        # we don't need to worry about args.binary's value because it
        # defaults to None
        if package_info is not None:
            args.binary = package_info.get('binary_name')
            package_name = package_info.get('name')
        # if we don't have a valid binary location, then exit
        if args.binary is None:
            print "Error: no binary found to daemonize"
            exit(1)
        centinel.daemonize.daemonize(package_name, args.binary)

    if args.sync:
        centinel.backend.sync(configuration.params)
    elif args.consent:
        user.informed_consent()
    else:
        client.run()
