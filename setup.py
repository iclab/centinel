import os
from setuptools import setup, find_packages

DESCRIPTION = """\
Centinel is a tool used to detect network interference, \
online information controls, and Internet censorship."""

setup(
    name="centinel",
    version="0.1.5.5.1",
    author="ICLab Developers",
    author_email="info@iclab.org",
    description=DESCRIPTION,
    license="MIT",
    keywords="censorship information controls network interference",
    url="https://www.github.com/iclab/centinel",
    packages=["centinel", "centinel.primitives",
              "centinel.vpn"],
    install_requires=["argparse >= 1.2.1",
                      "dnspython >= 1.11.0",
                      "requests >= 2.9.1",
                      "trparse >= 0.2.1",
                      "pycurl >= 7.19.5",
                      "urllib3 >= 1.9.1",
                      "dnspython >= 1.12.0",
                      "BeautifulSoup >= 3.2.1",
                      "httplib2 >= 0.9.2"],
    include_package_data=True,
    entry_points={
        'console_scripts': ['centinel=centinel.cli:run',
                            'centinel-vpn=centinel.vpn.cli:run']
    },
)
