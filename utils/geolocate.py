import requests

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
    response = requests.get('http://ip-api.com/line/' + ip.split(":")[0])
    if response.content.split('\n')[0] == "success":
	country = response.content.split('\n')[1]
        city = response.content.split('\n')[4]
    else:
	return False
    return country, city

def getmyip():
    response = requests.get("http://ipinfo.io/ip")
    return response.content.split()[0]