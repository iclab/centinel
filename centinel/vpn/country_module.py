import geonamescache
from difflib import SequenceMatcher 
from geopy.geocoders import Nominatim
from string import digits
import logging


def find_in_states(us_states, country):
	"""
	Given a country check if it is actually a US State
	:param us_states: a list of us states
	:param country: the country that we want to get its alpha code
	:return:
	"""
	for state in us_states:
		if(country in state):
			return 'US'
	return None

def manual_check(country):
	"""
	Some of the country names have spelling errors,
	This function manually fixes those

	:param country: the country that we want to get its alpha code
	:return the alpha2 country codes:
	"""
	if(country == "Angula"):
		return 'AO'
	if(country == "Bosnia"):
		return 'BA'
	if(country == "UAE"):
		return 'AE'
	if(country == "LosAngeles"):
		return 'US'
	if(country == "Virgin Islands (British)"):
		return 'VI'
	if(country == "Korea"):
		return 'KR'
	if(country == "PitcairnIslands"):
		return 'PN'
	if(country == "RepublicofSingapore"):
		return 'SG'
	if(country == "USA"):
		return 'US'
	if(country == "Coted`Ivoire"):
		return 'CI'
	if(country == "Congo"):
		return 'CD'
	if(country == "Palestine"):
		return 'PS'
	if(country == "RepublicofDjibouti"):
		return 'DJ'
	return None

def country_to_a2(country):
	"""
	This function converts country names to their alpha2 codes
	:param country: the country that we want to get its alpha code
	:return the alpha2 country codes:
	"""
	gc = geonamescache.GeonamesCache()
	countries = gc.get_countries()
	us_states = gc.get_us_states_by_names()

	# creating a dict between country name and alpha2 codes
	countries_dict = {}
	for item in countries:
		countries_dict[countries[item]['name']] = item
	countries_dict['United States of America'] = 'US'
	countries_dict['Deutschland'] = 'DE'
	countries_dict['UK'] = 'GB'

	if ',' in country:
		country = country.split(',')[0]
	iso2 = countries_dict.get(country)
	if (iso2 != None):
			return iso2
	else:
		iso2 = find_in_states(us_states,country)
		if(iso2 == None):
			iso2 = manual_check(country)
			if(iso2 == None):
				for known_country in countries_dict:
					if(SequenceMatcher(None, country, known_country).ratio()>0.70):
						iso2 = countries_dict.get(known_country)
						return iso2
					else:
						iso2 = None
				if (iso2 == None):
					try:
						# for removing numbers from country/city names
						country = country.translate(None, digits)
						geolocator = Nominatim()
						location = geolocator.geocode(country)
						location = (location.address).split(',')
						iso2 = (countries_dict.get(location[len(location)-1].strip()))
					except:
						# no mapping found
						return None

	return iso2
