#!/usr/bin/env python
import argparse
import getpass
import os

import centinel
import centinel.config
import centinel.daemonize

# Constants
DEFAULT_CONFIG_FILE = os.path.expanduser('~' + getpass.getuser() +
                                         "/.centinel/config.ini")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='Configuration file',
                        dest='config')
    no_verify_help = ("Disable certificate verification (NOT RECOMMENDED! "
                      "Use only when debugging.)")
    parser.add_argument('--no-verify', '-nv', help=no_verify_help,
                        action='store_true')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--version', '-v', action='version',
                       version="Centinel %s" % (centinel.__version__),
                       help='Print the installed version number')
    group.add_argument('--sync', help='Sync data with server',
                       action='store_true')
    consent_help = ("Give informed consent so that you can download "
                    "experiments from the researchers at ICLab and upload "
                    "results for analysis")
    group.add_argument('--informed-consent', help=consent_help,
                       dest='consent', default=False, action='store_true')

    daemon_help = ('Create cron jobs to run centinel in the background and '
                   'autoupdate. You must be root to use this functionality'
                   'By default, this will use /usr/local/bin/centinel-dev'
                   'for the binary location and will create an autoupdate '
                   'script')
    parser.add_argument('--daemonize', help=daemon_help, action='store_true',
                        dest='daemonize')
    binary_help = ('Name or location of the binary to use in the cron job '
                   'for centinel')
    parser.add_argument('--binary', help=binary_help,
                        default='/usr/local/bin/centinel-dev')
    update_help = ('Create an autoupdate script for the installed package. '
                   'Note that you must have installed from a pip package for '
                   'this to work correctly and you must also set the '
                   'daemonize option')
    parser.add_argument('--auto-update', action='store_false',
                        help=update_help, default="centinel-dev")

    args = parser.parse_args()
    if not args.daemonize and (args.auto_update != 'centinel-dev' or
                               args.binary != '/usr/local/bin/centinel-dev'):
        parser.error("--auto-update and --binary must be used with "
                     "--daemonize")
    return args


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
            print 'Configuration file does not exist.'

        if not ('version' in configuration.params and \
            configuration.params['version']['version'] == centinel.__version__):
            print ('Configuration file is from a different version of '
                   'Centinel.')
            configuration = centinel.config.Configuration()

        configuration.write_out_config(DEFAULT_CONFIG_FILE)

    client = centinel.client.Client(configuration.params)
    client.setup_logging()

    # disable cert verification if the flag is set
    if args.no_verify:
        configuration.params['server']['verify'] = False

    user = centinel.backend.User(configuration.params)
    # Note: because we have mutually exclusive arguments, we don't
    # have to worry about multiple arguments being called
    if args.sync:
        centinel.backend.sync(configuration.params)
    elif args.consent:
        user.informed_consent()
    elif args.daemonize:
        # if we don't have a valid binary location, then exit
        if not os.path.exists(args.binary):
            print "Error: no binary found to daemonize"
            exit(1)
        centinel.daemonize.daemonize(args.auto_update, args.binary)
    else:
        client.run()
