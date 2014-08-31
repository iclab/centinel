#!/usr/bin/env python
import sys
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
    centinel.client.setup_logging()

    if args.sync:
        centinel.backend.sync()
    else:
        centinel.client.run()
