#!/bin/bash

echo "Creating Centinel update package..."
rm -rf centinel_latest.tar.bz2
rm -rf centinel_latest
mkdir centinel_latest
mkdir centinel_latest/centinel
mkdir centinel_latest/centinel/test_primitives
mkdir centinel_latest/utils

cp -rf centinel/*.py centinel_latest/centinel
cp -rf centinel/centinel_service centinel_latest/centinel
cp -rf centinel/test_primitives/*.py centinel_latest/centinel/test_primitives
cp -rf utils/*.py centinel_latest/utils/
cp client_run.py centinel_latest/
cp init_client.py centinel_latest/
cp centinel.py centinel_latest/
cp .version centinel_latest/
cp .pydeps-mac centinel_latest/
cp .pydeps-linux centinel_latest/
cp centinel_client_ascii_art centinel_latest/
cp prepare.sh centinel_latest/
cp install_centinel.sh centinel_latest/
cp uninstall_centinel.sh centinel_latest/

tar -jcf centinel_latest.tar.bz2 centinel_latest/
rm -rf centinel_latest/
echo "Update package created."
