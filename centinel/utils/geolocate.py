import urllib

"""
    Geolocate an IP address.
	results:
	    [0]: country
	    [1]: city
    The HTTP response looks like this:
	
	Country: UNITED STATES (US)
	City: Aurora, TX

	Latitude: 33.0582
	Longitude: -97.5159
	IP: 12.215.42.19

"""
def geolocate(ip)
    response = urllib.urlopen('http://api.hostip.info/get_html.php?ip=' + ip + '&position=true').read()
    country = response.split('\n')[0].split(' ', 1)[1]
    city = response.split('\n')[1].split(' ', 1)[1]
    return country, city
