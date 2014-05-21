import os
from setuptools import setup, find_packages

DESCRIPTION = """\
Centinel is a tool used to detect network interference and internet censorship."""

setup(
    name = "centinel",
    version = "0.1.3",
    author = "Sathyanarayanan Gunasekaran",
    author_email = "gsathya@gatech.edu",
    description = DESCRIPTION,
    license = "MIT",
    keywords = "censorship network interference",
    url = "https://www.github.com/projectbismark/centinel",
    packages = ["centinel", "centinel.experiments", "centinel.utils"],
    install_requires = ["dnspython >= 1.11.0"],
    include_package_data = True,
    entry_points = {
        'console_scripts': ['centinel=centinel.client:run']
    },
)
