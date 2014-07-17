#!/bin/bash

client_output="2"
client_exec="./client_run.py"
centinel_dir=${PWD}

$client_exec $@
client_output=$?
if [ $client_output -eq 2 ]
then
    echo "Client update downloaded."
    if [ -f update.tar.bz2 ]
    then
	echo "Removing old Centinel directories..."
	mv update.tar.bz2 /tmp/centinel_update.tar.bz2
	cd ..
	rm -rf $centinel_dir
	echo "Done."
	echo "Unpacking new Centinel package..."
	rm -rf /tmp/centinel_update
	mkdir /tmp/centinel_update
	tar -jxf /tmp/centinel_update.tar.bz2 -C /tmp/centinel_update
	mv -f /tmp/centinel_update/centinel_latest $centinel_dir/
	rm /tmp/centinel_update.tar.bz2
	echo "Done."
	cd $centinel_dir
	./init_client.py --offline
    else
        echo "Update package not found!"
    fi
    echo "Restarting Centinel client..."
    ./client.sh $@
fi
