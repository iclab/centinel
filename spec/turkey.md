### Turkey

This tests checks for censorship in Turkey, by testing for

* DNS based blocking
* Blocking of Google's DNS nameserver

### Description

* Do a DNS lookup('A' record) with the url = twitter.com using the
  default nameserver
* Do a HTTPS GET request for a (previously known) tweet
* Check if a previously known string is present in the reponse body of
  the above request
* If the string is present, then no censorship is happening.
* Else if the string is not present, do all of the above, but use
  Google's nameserver(8.8.8.8) instead of the default nameserver
* If the string is not present, then Google DNS is blocked.

### Result

Stores the following information -

* Request
    + hostname
    + path
* Reponse 
    + status
    + headers
    + body
* Result
    + state of censorship
