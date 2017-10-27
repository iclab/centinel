""" Class for sanity check for vpn location"""
import logging
import os
import time
import csv
import pickle
import matplotlib
matplotlib.use('Agg')
from geopandas import *
from geopy.distance import vincenty
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import pyproj
import functools
import pycountry
from shapely.ops import transform as sh_transform
from shapely.geometry import Point, Polygon, box as Box
import zipfile
import requests
import StringIO

def sanity_check(args):
    """
    :param proxy_id:(str)
    :param iso_cnt:(str)
    :param ping_results:(dict) {anchors: [pings])
    :param anchors_gps:(dict) {anchors: (lat, long)}
    :param map:(dataframe)
    :return:
    """
    this_file, anchors, map, sanity_path, pickle_path = args
    try:
        start_time = time.time()
        with open(os.path.join(pickle_path, this_file), 'r') as f:
            json_data = pickle.load(f)
        proxy_name = json_data.keys()[0]
        iso_cnt = json_data[proxy_name]['cnt']
        pings = json_data[proxy_name]['pings']
        provider =json_data[proxy_name]['vpn_provider']
        proxy_ip = json_data[proxy_name]['ip_v4']
        checker = Checker(proxy_name, iso_cnt, sanity_path, provider, proxy_ip)
        points = checker.check_ping_results(pings, anchors)
        if len(points) == 0:
            logging.info("No valid ping results for %s" % proxy_name)
            return proxy_name, iso_cnt, -1
        logging.info("[%s] has %s valid pings from %s anchors"
                     %(proxy_name, len(points), len(pings)))
        circles = checker.get_anchors_region(points)
        proxy_region = checker.get_vpn_region(map)
        if proxy_region.empty:
            logging.info("[%s] Fail to get proxy region: %s" % (proxy_name, iso_cnt))
            return proxy_name, iso_cnt, -1
        results = checker.check_overlap(proxy_region, circles, this_file, anchors)
        tag = checker.is_valid(results)
        end_time = time.time() - start_time
        logging.info("[%s] sanity check takes for %.2fms" % (proxy_name, end_time))
    except Exception, e:
        logging.warning("[%s] Failed to sanity check: %s" % (this_file, str(e)))
        return "N/A", "N/A", -1
    return proxy_name, iso_cnt, tag

def load_map_from_shapefile(sanity_path):
    """
    Load all countries from shapefile
    (e.g.,  shapefile = 'map/ne_10m_admin_0_countries.shp')
    """
    logging.info("Loading a shapefile for the world map")
    shapefile = os.path.join(sanity_path, "ne_10m_admin_0_countries.shp")
    if not os.path.exists(shapefile):
        logging.info("Shape file does not exist, Downloading from server")
        shapefile_url = 'http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip'
        logging.info("Starting to download map shape file zip")
        try:
            r = requests.get(shapefile_url, stream=True)
            z = zipfile.ZipFile(StringIO.StringIO(r.content))
            z.extractall(sanity_path)
            logging.info("Map shape file downloaded")
        except Exception as exp:
            logging.error("Could not fetch map file : %s" % str(exp))
    temp = GeoDataFrame.from_file(shapefile)
    # print temp.dtypes.index
    map = temp[['ISO_A2', 'NAME', 'SUBREGION', 'geometry']]
    return map

class Checker:
    def __init__(self, proxy_id, iso, path, vpn_provider, ip):
        self.vpn_provider = vpn_provider
        self.proxy_id = proxy_id
        self.iso = iso
        self.gps = self._get_gps_of_proxy()
        self.path = path
        self.ip = ip

    def get_vpn_region(self, map):
        """
        Get a region of given iso country
        """
        # logging.info("Getting vpn region from a map")
        region = map[map.ISO_A2 == self.iso].geometry
        if region.empty:
            cnt = pycountry.countries.get(alpha2=self.iso)
            region = map[map.NAME == cnt.name].geometry
        if region.empty:
            logging.info("Fail to read country region: %s (%s)" % (self.iso, cnt))
            return None
        df = geopandas.GeoDataFrame({'geometry': region})
        df.crs = {'init': 'epsg:4326'}
        return df

    def _get_gps_of_proxy(self):
        """ Return vp's gps
        """
        vpn_gps = tuple()
        try:
            geolocator = Nominatim()
            location = geolocator.geocode(self.iso)
            if location == None:
                logging.info("Fail to get gps of location %s" %self.iso)
                return None
            vpn_gps = (location.latitude, location.longitude)
        except GeocoderTimedOut as e:
            logging.info("Error geocode failed: %s" %(e))
        return vpn_gps

    def _disk(self, x, y, radius):
        return Point(x, y).buffer(radius)

    def get_anchors_region(self, points):
        """ Get anchors region
        (referred from zack's paper & code Todo: add LICENSE?)
        https://github.com/zackw/active-geolocator
        Note that pyproj takes distances in meters & lon/lat order.
        """
        # logging.info("Starting to draw anchors region")
        wgs_proj = pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
        ## Sort based on distance. if there is no distance, then sort with min delay
        if points[0][0] != 0:
            points.sort(key=lambda tup: tup[0]) #closest to the proxy
        else:
            points.sort(key=lambda tup: tup[1]) #order of min time
        circles = list()
        count = 0
        for dist, min_delay, lat, lon, radi, anchor_name in points:
            count += 1
            # create azimuthal equidistant projector for each anchors
            aeqd = pyproj.Proj(proj='aeqd', ellps='WGS84', datum='WGS84',
                               lat_0=lat, lon_0=lon)
            try:
                # draw a disk (center = long/lat, radius)
                disk = sh_transform(
                    functools.partial(pyproj.transform, aeqd, wgs_proj),
                    self._disk(0, 0, radi * 1000))  # km ---> m
                north, south, west, east = 90., -90., -180, 180
                boundary = np.array(disk.boundary)
                i = 0
                while i < boundary.shape[0] - 1:
                    if abs(boundary[i + 1, 0] - boundary[i, 0]) > 180:
                        pole = south if boundary[i, 1] < 0 else north
                        west = west if boundary[i, 0] < 0 else east
                        east = east if boundary[i, 0] < 0 else west
                        boundary = np.insert(boundary, i + 1, [
                            [west, boundary[i, 1]],
                            [west, pole],
                            [east, pole],
                            [east, boundary[i + 1, 1]]
                        ], axis=0)
                        i += 5
                    else:
                        i += 1
                disk = Polygon(boundary).buffer(0)
                # In the case of the generated disk is too large
                origin = Point(lon, lat)
                if not disk.contains(origin):
                    df1 = geopandas.GeoDataFrame({'geometry': [Box(-180., -90., 180., 90.)]})
                    df2 = geopandas.GeoDataFrame({'geometry': [disk]})
                    df3 = geopandas.overlay(df1, df2, how='difference')
                    disk = df3.geometry[0]
                    assert disk.is_valid
                    assert disk.contains(origin)
                circles.append((lat, lon, radi, disk, anchor_name, dist, min_delay))
            except Exception as e:
                logging.debug("Fail to get a circle %s" %self.proxy_id)
        return circles

    def check_overlap(self, proxy_region, circles, ping_filename, anchors):
        """ Check overlap between proxy region and anchors' region.
        If there is an overlap check how much they are overlapped,
        otherwise, check how far the distance is from a proxy.
        :return results(list): if True: the percentage of overlapped area to a country
                                 False: the distance (km) between a country and expected range
        """
        # logging.info("Starting to check overlap")
        results = list()
        for lat, lon, radi, this_circle, anchor_name, distance, min_delay in circles:
            df_anchor = geopandas.GeoDataFrame({'geometry': [this_circle]})
            overlap = geopandas.overlay(proxy_region, df_anchor, how="intersection")
            if overlap.empty:
                aeqd = pyproj.Proj(proj='aeqd', ellps='WGS84', datum='WGS84',
                                   lat_0=lat, lon_0=lon)
                wgs_proj = pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")  ##4326 -- 2d
                ## country
                azimu_cnt = sh_transform(
                    functools.partial(pyproj.transform, wgs_proj, aeqd),
                    proxy_region.geometry.item())
                ## min_distance
                azimu_anchor = self._disk(0, 0, radi * 1000)  #km ---> m
                gap = azimu_anchor.distance(azimu_cnt) / float(1000)   #km
                results.append({'anchor_name': anchor_name, 'distance': distance, 'proxy_name': self.proxy_id,
                                'min_delay': min_delay, 'truth': False, 'extra': gap, 'anchor_gps': (lat, lon),
                                'anchor_ip': anchors[anchor_name]['ip_v4'], 'radius': radi, 'proxy_ip': self.ip,
                                'anchor_cnt': (anchors[anchor_name]['city'], anchors[anchor_name]['country']),
                                'proxy_country': self.iso})
            else:
                ## area
                area_cnt = proxy_region['geometry'].area#/10**6 #km/sqr
                area_cnt = sum(area_cnt.tolist())
                area_overlap = overlap['geometry'].area#/10**6 #km/sqr
                area_overlap = sum(area_overlap.tolist())
                overlapped = area_overlap/area_cnt
                results.append({'anchor_name': anchor_name, 'distance': distance, 'proxy_name': self.proxy_id,
                                'min_delay': min_delay, 'truth': True, 'extra': overlapped, 'anchor_gps': (lat, lon),
                                'anchor_ip': anchors[anchor_name]['ip_v4'], 'radius': radi, 'proxy_ip': self.ip,
                                'anchor_cnt': (anchors[anchor_name]['city'], anchors[anchor_name]['country']),
                                'proxy_country': self.iso})
        pickle_path = os.path.join(self.path, 'sanity/'+self.vpn_provider)
        if not os.path.exists(pickle_path):
            os.makedirs(pickle_path)
        with open(os.path.join(pickle_path, ping_filename+'.csv'), 'w') as f:
            writer = csv.writer(f)
            writer.writerow(('proxy_name','proxy_ip','proxy_country','truth','extra',
                             'anchor_name','anchor_ip','anchor_cnt','anchor_gps','distance','min_delay','radius'))
            for this in results:
                writer.writerow((this['proxy_name'],this['proxy_ip'],this['proxy_country'],
                                 this['truth'],this['extra'],
                                 this['anchor_name'],this['anchor_ip'],this['anchor_cnt'],
                                 this['anchor_gps'],this['distance'],this['min_delay'],this['radius']))
        with open(os.path.join(pickle_path, ping_filename), 'w') as f:
            pickle.dump(results, f)
            # logging.info("Pickle file successfully created.")
        return results

    def _calculate_radius(self, time_ms):
        """
        (the number got from zack's paper & code)
        Network cable's propagation speed: around 2/3c = 199,862 km/s
        + processing & queueing delay --> maximum speed: 153,000 km/s (0.5104 c)
        """
        C = 299792 # km/s
        speed = np.multiply(0.5104, C)
        second = time_ms/float(1000)
        dist_km = np.multiply(speed, second)
        return dist_km

    def check_ping_results(self, results, anchors_gps):
        """
        Because the equator circumference is 40,074.275km.
        the range cannot be farther than 20,037.135km.
        If there are anomalies pings (<3.0ms or >130.0ms), remove.
        Otherwise, return latitude and longitude of vps, radius derived from ping delay.
        Return points(list): (lat, lon, radius)
        """
        points = list()
        for anchor, pings in results.iteritems():
            valid_pings = list()
            for this in pings:
                # remove anomalies
                ping = float(this.split(' ')[0])
                owtt = ping/2.0
                if float(owtt) >= 3.0 and float(owtt) <= 130.0:
                    valid_pings.append(owtt)
            if len(valid_pings) == 0:
                logging.debug("no valid pings results of anchor %s" %anchor)
                continue
            min_delay = min(valid_pings)
            radi = self._calculate_radius(min_delay)
            if anchor not in anchors_gps:
                logging.debug("no gps for anchor %s" %anchor)
                continue
            # calculate the distance(km) between proxy and anchor
            distance = 0
            anchor_gps = (anchors_gps[anchor]['latitude'], anchors_gps[anchor]['longitude'])
            if len(self.gps) != 0:
                distance = vincenty(anchor_gps, self.gps).km
            points.append((distance, min_delay, anchor_gps[0], anchor_gps[1], radi, anchor))
        if len(points) == 0:
            logging.debug("no valid pings results")
            return []
        return points

    def is_valid(self, results):
        """
        Need reasonable threshold to answer the validation of location
        For now, we say it is valid if 90% of 30 nearest anchors are True
        """
        # logging.info("checking validation")
        total = 0
        count_valid = 0
        limit = 30
        for this in results:
            valid = this['truth']
            aux = this['extra']
            total += 1
            if valid:
                count_valid += 1
            if total == limit:
                break
        frac = count_valid/float(limit)
        if frac >= 0.9:
            return True
        else:
            return False