#!/usr/bin/env python
import argparse
import logging
import getpass
import os
import os.path
import sys

import centinel
import centinel.config
import centinel.daemonize

PID_FILE = "/tmp/centinel.lock"

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
                       version="Centinel %s" % centinel.__version__,
                       help='Print the installed version number')
    group.add_argument('--sync', help='Sync data with server',
                       action='store_true')
    consent_help = ("Give informed consent so that you can download "
                    "experiments from the researchers at ICLab and upload "
                    "results for analysis")
    group.add_argument('--informed-consent', help=consent_help,
                       dest='consent', default=False, action='store_true')
    daemon_help = ('Create cron jobs to run Centinel in the background and '
                   'autoupdate the package. You need to run this command as '
                   'root in order to setup this functionality. '
                   'By default, this will use /usr/local/bin/centinel '
                   'for the binary location and will create an autoupdate '
                   'script.')
    parser.add_argument('--daemonize', help=daemon_help, action='store_true',
                        dest='daemonize')
    user_help = ('Using this option with --daemonize will make the '
                 'cron job created to run Centinel as the specified user '
                 'instead of root. You will still need to run this '
                 'command as root to setup this functionality. '
                 'By default, root is used to run both daemonized scripts.')
    parser.add_argument('--user', help=user_help, default="root")
    verbose_help = ('Verbose logging')
    parser.add_argument('--verbose', '-V', help=verbose_help,
                        action='store_true', dest='verbose')
    binary_help = ('Name or location of the binary to use in the cron job '
                   'for Centinel')
    parser.add_argument('--binary', help=binary_help,
                        default='/usr/local/bin/centinel')
    update_help = ('Create an autoupdate script for the installed package. '
                   'Note that you must have installed from a pip package for '
                   'this to work correctly and you must also set the '
                   'daemonize option')
    parser.add_argument('--auto-update', action='store_false',
                        help=update_help, default="centinel")
    group.add_argument('--update-config', help='Update configuration file',
                       action='store_true')
    meta_help = ('Add custom meta tags to results. '
                 'Format is: key1:value1,key2:value2,... without spaces')
    parser.add_argument('--meta', '-m', help=meta_help, dest='custom_meta')

    args = parser.parse_args()
    if (not args.daemonize and 
        (args.auto_update != 'centinel' or
         args.binary != '/usr/local/bin/centinel' or
         args.user != "root")):
        parser.error("--auto-update, --user, and --binary must be used with "
                     "--daemonize")
    return args


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
        sys.stderr.write("Failed to remove lock file %s: %s\n" % (PID_FILE, exp))


def _run():
    """Entry point for package and cli uses"""

    args = parse_args()

    # parse custom parameters
    custom_meta = None
    if args.custom_meta:
        print "Adding custom parameters:"
        custom_meta = {}
        try:
            for item in args.custom_meta.split(','):
                key, value = item.split(':')
                custom_meta[key] = value
                print 'key: %s, value: %s' % (key, value)
        except Exception as e:
            sys.stderr.write("ERROR: Can not parse custom meta tags! %s\n" % (str(e)))

    # we need to store some persistent info, so check if a config file
    # exists (default location is ~/.centinel/config.ini). If the file
    # does not exist, then create a new one at run time
    configuration = centinel.config.Configuration()
    if args.config:
        configuration.parse_config(args.config)
    else:
        # if the file does not exist, then the default config file
        # will be used
        new_configuration = None
        if os.path.exists(DEFAULT_CONFIG_FILE):
            configuration.parse_config(DEFAULT_CONFIG_FILE)
        else:
            print 'Configuration file does not exist. Creating a new one.'
            new_configuration = centinel.config.Configuration()

        if not ('version' in configuration.params and
                configuration.params['version']['version'] == centinel.__version__):
            if not args.update_config:
                print ('WARNING: configuration file is from '
                       'a different version (%s) of '
                       'Centinel. Run with --update-config to update '
                       'it.' % (configuration.params['version']['version']))
            else:
                new_configuration = centinel.config.Configuration()
                backup_path = DEFAULT_CONFIG_FILE + ".old"
                new_configuration.update(configuration, backup_path)

        if new_configuration is not None:
            configuration = new_configuration
            configuration.write_out_config(DEFAULT_CONFIG_FILE)
            print 'New configuration written to %s' % (DEFAULT_CONFIG_FILE)
            if args.update_config:
                sys.exit(0)

    if args.verbose:
        if 'log' not in configuration.params:
            configuration.params['log'] = dict()
        configuration.params['log']['log_level'] = logging.DEBUG

    # add custom meta values from CLI
    if custom_meta is not None:
        if 'custom_meta' in configuration.params:
            configuration.params['custom_meta'].update(custom_meta)
        else:
            configuration.params['custom_meta'] = custom_meta

    centinel.conf = configuration.params
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
        centinel.daemonize.daemonize(args.auto_update, args.binary,
            args.user)
    else:
        client.run()

if __name__ == "__main__":
    run()
