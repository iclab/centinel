#!/bin/sh

echo "Removing old dirs."
rm -rf /opt/centinel
echo "Making new dir."
mkdir /opt/centinel
echo "Copying new contents."
cp -rf utils /opt/centinel
cp -rf centinel /opt/centinel/centinel
cp -rf centinel.py /opt/centinel
cp -rf client_run.py /opt/centinel
cp -rf init_client.py /opt/centinel
cp -rf prepare.sh /opt/centinel
cp -rf centinel_client_ascii_art /opt/centinel
cp -rf .pydeps-linux /opt/centinel
cp -rf .pydeps-mac /opt/centinel
cp -rf .version /opt/centinel
cp -rf centinel/centinel_service /etc/init.d/centinel

echo "Preparing and initializing."
/opt/centinel/prepare.sh
su - root -c /opt/centinel/init_client.py

echo "Stopping service."
service centinel stop

echo "Installing service."
update-rc.d -f centinel remove
update-rc.d centinel defaults

echo "Starting service."
service centinel start

echo "Done"