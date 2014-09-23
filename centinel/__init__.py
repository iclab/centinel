#!/usr/bin/python

import centinel.backend
import centinel.config
import centinel.client


def run():
    """This is the entry point for the build script, aka where you can run
    everything without specifying any arguments

    """
    configuration = centinel.config.Configuration()
    client = centinel.client.Client(configuration.params)
    client.setup_logging()
    # to make everything self contained, we are syncing before and
    # after each run
    centinel.backend.sync(configuration.params)
    client.run()
    centinel.backend.sync(configuration.params)
