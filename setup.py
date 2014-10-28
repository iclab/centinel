import os
from setuptools import setup, find_packages

DESCRIPTION = """\
Centinel is a tool used to detect network interference and internet censorship."""

setup(
    name = "centinel-dev",
    version = "0.1.4.10",
    author = "Sathyanarayanan Gunasekaran",
    author_email = "gsathya@gatech.edu",
    description = DESCRIPTION,
    license = "MIT",
    keywords = "censorship network interference",
    url = "https://www.github.com/iclab/centinel",
    packages = ["centinel", "centinel.experiments", "centinel.primitives",
                "centinel.vpn"],
    install_requires = ["dnspython >= 1.11.0", "requests >= 2.0.0"],
    include_package_data = True,
    entry_points = {
        'console_scripts': ['centinel-dev=centinel.cli:run',
                            'centinel-vpn-dev=centinel.vpn.cli:run']
    },
)
