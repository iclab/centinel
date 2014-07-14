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

#### How to make a test

    * The file must end in .cfg
    $ >newTest.cfg

    * A list of URLs should be written to the file like this:
    * Every URL after the first one must be indented

    [URLS]
    url_list = google.com
	yahoo.com
	rpanah.ir

    * You can add different tests by adding their names in square brackets.
    * Example: [DNS]

    * different parameters can be added below the test name like this:
    * Don't include comments following the '#'s

    [DNS] # (Name of the test)
    timeout = 5 # Specifies timeout
    resolver = 8.8.8.8 # Another parameter.This one specifies the resolver ip

    # Parameters are optional, but add flexibility to the tests

##### Full Test list and parameters

    # [DNS]- Performs a DNS query on the list of URLs
	 ---Parameters---
	* timeout - the number of seconds before the dns request times out
	* record - the dns record type ("A" by default though not compatible with every type of record)
	* resolver - the ip address of the dns resolver

    # [Ping] - Pings the list of urls and records the results
	---Parameters---
	* packets - the number of packets to be sent (1 by default)
	* timeout - time in seconds before the ping times out and ends before receiving a response (10 by default)
    
    # [HTTP] - performs an HTTP GET and records the results
	* (There are no parameters for this test at the moment)

    # [Traceroute] - Performs a traceroute and records the results
	---Parameters---
	* max_hops - The max ttl/hops in the traceroute (30 by default)
	* start_hop - The starting ttl/hop (1 by default)
	* timeout - the timeout in seconds at each hop before receiving a response (10 by default)
    
    # [TCP] - Attempts to connect the urls through tcp connections
	---Parameters---
	* port - the port in which the tcp connection is made


#### Example Test File ####
[URLS]
url_list = google.com
    yahoo.com
    rpanah.ir

[HTTP]

[DNS]
record = A
resolver = 8.8.8.8

[Traceroute]
timeout = 10

[TCP]

[Ping]


	
    

    

    
