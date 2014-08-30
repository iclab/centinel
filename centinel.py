#!/usr/bin/env python
import argparse

import centinel

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sync', help='Sync data with server',
                        action='store_true')
    parser.add_argument('--version', '-v', action='version',
                        version="Centinel %s" % (centinel.__version__),
                        help='Sync data with server')
    parser.add_argument('--experiment', '-e', help='Experiment name',
                        nargs="*", dest="experiments")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    #XXX: There's absolutely no need to do all this version checking
    try:
        recommended_version = centinel.backend.get_recommended_version()
        if centinel.__version__ < recommended_version:
            print "Latest version of centinel is %s. Update now" % (recommended_version)
    except Exception, e:
        print "Unable to get latest version: %s" % str(e)

    if args.sync:
        centinel.backend.sync()

    centinel.client.run()
