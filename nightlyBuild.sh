#!/bin/bash -eu
#
# nightlyBuild.sh: script to build and upload the latest version of the package

# first, test that we can successfully build the repo (since we are using
# bash's -e flag, this will fail if we cannot build from the repo
pip install --no-install --upgrade -e git+https://github.com/iclab/centinel.git#egg=centinel_client
git pull --rebase origin master
python setup.py sdist bdist_egg
twine upload dist/*

