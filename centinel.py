#!/usr/bin/env python
import logging
import centinel

if __name__ == "__main__":
    #XXX: There's absolutely no need to do all this version checking
    recommended_version = centinel.backend.get_recommended_version()
    if centinel.__version__ < recommended_version:
        logging.warn("Latest version of centinel is %s. Update now" %
                     (recommended_versions))

    centinel.client.run()
