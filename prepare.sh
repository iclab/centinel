#! /bin/sh


if [ `uname -s` = "Linux" ]; then
    for dep in `cat .pydeps-linux`
    do
	sudo apt-get install -y python-$dep
    done;
fi;

if [ `uname -s` = "Darwin" ]; then
    for dep in `cat .pydeps-mac`
    do
        pip install $dep
    done;
    sudo port install scapy
fi;
