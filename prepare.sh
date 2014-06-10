#! /bin/sh


if [ `uname -s` = "Linux" ]; then
    for dep in `cat .pydeps`
    do
	sudo apt-get install python-$dep
    done;
fi;

if [ `uname -s` = "Darwin" ]; then
    for dep in `cat .pydeps`
    do
        pip install $dep
    done;
    sudo port install scapy
fi;

sudo python setup.py build
