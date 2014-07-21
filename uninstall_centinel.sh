#!/bin/sh

echo "Stopping service."
service centinel stop

echo "Removing service."
update-rc.d -f centinel remove

echo "Removing old dirs."
rm -rf /opt/centinel

echo "Done"