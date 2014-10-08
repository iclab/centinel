#!/usr/bin/env python
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
    user = centinel.backend.User(configuration.params)
    # Note: because we have mutually exclusive arguments, we don't
    # have to worry about multiple arguments being called
    if args.sync:
        centinel.backend.sync(configuration.params)
    elif args.consent:
        user.informed_consent()
    else:
        client.run()
