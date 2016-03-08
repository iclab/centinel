### Centinel

Centinel is a tool used to detect network interference and internet
censorship.

#### Install and usage
##### Debian
    $ sudo apt-get install python-pip libssl-dev swig python-dev libffi-dev tcpdump libcurl4-openssl-dev traceroute
    $ sudo pip install -U pip
    $ sudo pip install centinel
    $ centinel

##### Fedora 23
    $ sudo dnf install python-devel libcurl-devel openssl-devel swig libffi-devel tcpdump traceroute gcc redhat-rpm-config
    $ sudo pip install -U pip
    
    $ sudo su
    $ export PYCURL_SSL_LIBRARY=nss
    $ pip install pycurl
    $ exit
    
    $ sudo pip install centinel

##### OSX
    $ sudo pip install centinel
    $ centinel

##### Latest development version
    * git clone https://github.com/iclab/centinel.git
    # install dnspython, requests
    * sudo python setup.py install
    * python centinel.py

#### Supported platforms

    * Linux/OS X
    * BISmark Routers
    * Android
