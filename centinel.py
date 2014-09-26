#!/usr/bin/env python
import argparse
import getpass
import os
import sys

import centinel
import centinel.config

# Constants
DEFAULT_CONFIG_FILE = os.path.expanduser('~' + getpass.getuser())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sync', help='Sync data with server',
                        action='store_true')
    parser.add_argument('--version', '-v', action='version',
                        version="Centinel %s" % (centinel.__version__),
                        help='Sync data with server')
    parser.add_argument('--experiment', '-e', help='Experiment name',
                        nargs="*", dest="experiments")
    parser.add_argument('--config', '-c', help='Configuration file',
                        dest='config')

    give_consent_help = ('Give informed consent so you can upload results to '
                         'the researchers at ICLab and download their '
                         'experiments')
    parser.add_argument('--give-informed-consent', help=give_consent_help,
                        dest='given_consent', action='store_true',
                        default=None)
    clear_consent_help = ('Choose not to give consent to Centinel and clear '
                          'the consent flag so that you can run Centinel. '
                          'Note: This is *not* advised; you are undertaking '
                          'a lot of risk and you will not be able to upload '
                          'results to ICLab or download experiments. Even if '
                          'you are choosing not to upload your results, '
                          'please visit our site to better understand the '
                          'risks you face.')
    parser.add_argument('--do-not-give-informed-consent',
                        help=clear_consent_help, dest='given_consent',
                        action='store_true', default=None)

                        
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

    client = centinel.client.Client(configuration.params)
    client.setup_logging()

    if args.sync:
        centinel.backend.sync(configuration.params)
    elif args.given_consent is not None:
        client.informed_consent(args.given_consent)
    else:
        client.run()
