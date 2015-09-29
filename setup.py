import os
from setuptools import setup, find_packages

DESCRIPTION = """\
Centinel is a tool used to detect network interference, \
online information controls, and Internet censorship."""

setup(
    name = "centinel",
    version = "0.1.5.4",
    author = "ICLab Developers",
    author_email = "info@iclab.org",
    description = DESCRIPTION,
    license = "MIT",
    keywords = "censorship information controls network interference",
    url = "https://www.github.com/iclab/centinel",
    packages = ["centinel", "centinel.primitives",
                "centinel.vpn"],
    install_requires = ["argparse >= 1.2.1",
                        "m2crypto >= 0.22.0",
                        "dnspython >= 1.11.0",
                        "requests >= 2.5.1",
                        "trparse >= 0.2.1"],
    include_package_data = True,
    entry_points = {
        'console_scripts': ['centinel=centinel.cli:run',
                            'centinel-vpn=centinel.vpn.cli:run']
    },
)
