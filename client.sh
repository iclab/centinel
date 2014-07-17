#!/bin/bash

client_output="2"
client_exec="./client_run.py"
while [ $client_output -eq 2 ]
do
    $client_exec $@
    client_output=$?
    if [ $client_output -eq 2 ]
    then
	echo "Client update downloaded."
	if [ -f update.tar.bz2 ]
	then
	    echo "Removing old Centinel files..."
	    rm -rf centinel
	    rm -rf client_run.py
	    echo "Done."
	    echo "Unpacking new Centinel package..."
	    tar -jzvf update.tar.bz2
	    echo "Done."
	    echo "Restarting Centinel client..."
	else
	    echo "Update package not found!"
	fi
    fi
done

echo "Exiting..."