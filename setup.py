import os
from setuptools import setup

DESCRIPTION = """\
Centinel is a tool used to detect network interference and internet censorship."""

setup(
    name = "centinel",
    version = "0.1",
    author = "Sathyanarayanan Gunasekaran",
    author_email = "gsathya@gatech.edu",
    description = DESCRIPTION,
    license = "MIT",
    keywords = "censorship network interference",
    url = "https://www.github.com/projectbismakr/centinel",
    packages = ['experiments'],
    install_requires = ["dnspython >= 1.11.0"],
    entry_points = {
        'console_scripts': ['centinel = centinel:run']
    },
)
