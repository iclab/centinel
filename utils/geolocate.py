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
def geolocate(ip):
    response = urllib.urlopen('http://ip-api.com/line/' + ip).read()
    country = response.split('\n')[0].split('\n')[1]
    city = response.split('\n')[1].split('\n')[4]
    return country, city
