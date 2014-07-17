### Centinel Client

Centinel is a tool used to detect network interference and internet
censorship.

#### Install and usage

    # acquire the latest development version
    * git clone https://github.com/iclab/centinel-iclab.git
    
    # prepare and install dependencies
    * ./prepare.sh

    # initialize Centinel and exchange keys with Sirocco server
    * ./init_client.py

    # run Centinel Client
    * ./client.sh [experiment 1] [experiment 2] ...
	(running without arguments will run the client daemon and connect to the server)

#### Supported platforms

    * Linux/OS X
    * BISmark Routers
    * Android

#### How to make a test

    * The file must either end in .cfg or .py and be placed in ~/.centinel/custom_experiments/
    $ >centinel/custom_experiments/newTest.cfg

    * If writing a Python configuration:
    * [to be added]

    * If writing a test configuration:

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

    # [Ping] - Pings the list of urls and records the results (uses system ping)
	---Parameters---
	* packets - the number of packets to be sent (1 by default)
	* timeout - time in seconds before the ping times out and ends before receiving a response (10 by default)
    
    # [HTTP] - performs an HTTP GET and records the results
	* (There are no parameters for this test at the moment)

    # [Traceroute] - Performs a traceroute and records the results
	---Parameters---
	* max_hops - The max TTL/hops in the traceroute (30 by default)
	* start_hop - The starting TTL/hop (1 by default)
	* timeout - the timeout in seconds at each hop before receiving a response (10 by default)
    
    # [TCP] - Attempts to connect to the URLs through TCP connections
	---Parameters---
	* port - the port to which the TCP connection is made


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

