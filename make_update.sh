#!/bin/bash

echo "Creating Centinel update package..."
rm -rf centinel_latest.tar.bz2
tar -jcf centinel_latest.tar.bz2 centinel/ utils/ client_run.py client.sh .version .pydeps-mac .pydeps-linux centinel_client_ascii_art prepare.sh init_client.py
echo "Update package created."