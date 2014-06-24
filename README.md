### Centinel

Centinel is a tool used to detect network interference and internet
censorship.

#### Install and usage
    $ sudo apt-get install python-setuptools

    # via pip
    $ sudo pip install centinel
    $ centinel_client

    # latest development version
    * git clone https://github.com/projectbismark/centinel.git
    * # install dnspython
        * Debian - $ sudo apt-get python-dnspython
        * OSX    - $ pip install dnspython
    * python centinel_client.py [experiment 1] [experiment 2] ...
	(running without arguments will run all experiments)

#### Supported platforms

    * Linux/OS X
    * BISmark Routers
    * Android
