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
	    echo "Removing old Centinel directories..."
	    rm -rf centinel
	    rm -rf utils
	    echo "Done."
	    echo "Unpacking new Centinel package..."
	    tar -jxvf update.tar.bz2
	    echo "Done."
	    echo "Restarting Centinel client..."
	else
	    echo "Update package not found!"
	fi
    fi
done

echo "Exiting..."