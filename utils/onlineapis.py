import requests

"""
    Geolocate an IP address.
	results:
	    [0]: country
	    [1]: city
"""
def geolocate(ip):
    response = requests.get('http://ip-api.com/line/' + ip.split(":")[0])
    if response.content.split('\n')[0] == "success":
	country = response.content.split('\n')[1]
        city = response.content.split('\n')[4]
    else:
	return False
    return country, city

"""
    Get external IP address.
"""
def getmyip():
    response = requests.get("http://ipinfo.io/ip")
    return response.content.split()[0]

"""
    Get the current EST time.
"""
def getESTTime():
    response = requests.get("http://www.timeapi.org/est/now")
    return response.content.split()[0]
