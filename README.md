### Centinel

Centinel is a tool used to detect network interference and internet
censorship.

#### Install
    $ sudo apt-get install python-setuptools
    
    # via pip
    $ sudo pip install centinel 

    # latest development version
    * git clone https://github.com/projectbismark/centinel.git
    * # install dnspython
        * Debian - $ sudo apt-get python-dnspython
        * OSX    - $ pip install dnspython
	* OSX	 - $ pip install requests
    * cd centinel/
    * sudo python setup.py install

#### Usage
    # if you've installed it already, use this:
    * $ centinel

    # if you just want to run (without installing), use these:
    
    * $ ./prepare.sh
    * $ sudo python centinel.py

#### Supported platforms

    * Linux/OS X
    * BISmark Routers
    * Android
