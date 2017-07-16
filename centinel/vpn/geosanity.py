""" Class for sanity check for vpn location"""
import datetime
import logging
import pickle
from geopandas import *
from geopy.distance import vincenty
from geopy.geocoders import Nominatim
import pyproj
import functools
from shapely.ops import transform as sh_transform
from shapely.geometry import Point, Polygon, box as Box



def sanity_check(proxy_id, iso_cnt, ping_results, anchors_gps, map):
    """
    :param proxy_id:(str)
    :param iso_cnt:(str)
    :param ping_results:(dict) {anchors: [pings])
    :param anchors_gps:(dict) {anchors: (lat, long)}
    :param map:(dataframe)
    :return:
    """
    checker = Checker(proxy_id, iso_cnt)
    # points = checker.check_ping_results(results, anchors_gps)
    points = checker.check_ping_results(ping_results, anchors_gps)
    if len(points) == 0:
        logging.debug("No valid ping results for %s" % proxy_id)
        return -1
    circles = checker.get_anchors_region(points)
    proxy_region = checker.get_vpn_region(map)
    if proxy_region.empty:
        logging.debug("Fail to get proxy region: %s" % iso_cnt)
        return -1
    results = checker.check_overlap(proxy_region, circles)
    return checker.is_valid(results)
    # time_now = str(datetime.datetime.now()).split(' ')[0]
    # with open("results_" + proxy_id + "_" + time_now + ".pickle", "w") as f:
    #   pickle.dump(results, f)

def load_map_from_shapefile(shapefile):
    """
    Load all countries from shapefile
    (e.g.,  shapefile = 'map/ne_10m_admin_0_countries.shp')
    """
    temp = GeoDataFrame.from_file(shapefile)
    map = temp[['ISO_A2', 'NAME', 'SUBREGION', 'geometry']]
    return map


def get_gps_of_anchors(anchors):
    """
    Get gps of all anchors
    Note: geopy library has a limitation for query in a certain time.
          While testing, better to store the query results so that we can reduce the number of query.
    """
    anchors_gps = dict()
    count = 0
    try:
        with open("gps_of_anchors.pickle", "r") as f:
            anchors_gps = pickle.load(f)
    except:
        for anchor, item in anchors.iteritems():
            count += 1
            logging.debug(
                "Retrieving... %s(%s/%s): %s" % (anchor, count, len(anchors), item['city'] + ' ' + item['country']))
            geolocator = Nominatim()
            location = geolocator.geocode(item['city'] + ' ' + item['country'])
            if location == None:
                location = geolocator.geocode(item['country'])
            if location == None:
                logging.debug("Fail to read gps of %s" %anchor)
            anchors_gps[anchor] = (location.latitude, location.longitude)
        with open("gps_of_anchors.pickle", "w") as f:
            pickle.dump(anchors_gps, f)
    return anchors_gps


class Checker:
    def __init__(self, proxy_id, iso):
        self.proxy_id = proxy_id
        self.iso = iso
        self.gps = self._get_gps_of_proxy()

    def get_vpn_region(self, map):
        """
        Get a region of given iso country
        """
        region = map[map.ISO_A2 == self.iso].geometry
        if region.empty:
            logging.info("Fail to read country region: %s" % self.iso)
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
                logging.debug("Fail to get gps of location %s" %self.iso)
                return None
            vpn_gps = (location.latitude, location.longitude)
        except:
            logging.debug("Fail to get gps of proxy")
        return vpn_gps

    def _disk(self, x, y, radius):
        return Point(x, y).buffer(radius)

    def get_anchors_region(self, points):
        """ Get anchors region
        (referred from zack's paper & code Todo: add LICENSE?)
        https://github.com/zackw/active-geolocator
        Note that pyproj takes distances in meters & lon/lat order.

        """
        wgs_proj = pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
        ## Sort based on distance. if there is no distance, then sort with min delay
        if points[0][0] != 0:
            points.sort(key=lambda tup: tup[0]) #closest to the proxy
        else:
            points.sort(key=lambda tup: tup[1]) #order of min time
        circles = list()
        count = 0
        for dist, min_delay, lat, lon, radi in points:
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
                circles.append((lat, lon, radi, disk))
            except Exception as e:
                logging.debug("Fail to get a circle %s" %self.proxy_id)
        return circles

    def check_overlap(self, proxy_region, circles):
        """ Check overlap between proxy region and anchors' region.
        If there is an overlap check how much they are overlapped,
        otherwise, check how far the distance is from a proxy.
        :return results(list): if True: the percentage of overlapped area to a country
                                 False: the distance (km) between a country and expected range
        """
        results = list()
        for lat, lon, radi, this_circle in circles:
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
                gap = azimu_anchor.distance(azimu_cnt) / 1000    #km
                results.append((False, gap))
            else:
                ## area
                area_cnt = proxy_region['geometry'].area#/10**6 #km/sqr
                area_cnt = sum(area_cnt.tolist())
                area_overlap = overlap['geometry'].area#/10**6 #km/sqr
                area_overlap = sum(area_overlap.tolist())
                stack = area_overlap/area_cnt
                results.append((True, stack))
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
        Todo: points (distance, lat, long, radius)
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
            if len(self.gps) != 0:
                distance = vincenty(anchors_gps[anchor], self.gps).km
            points.append((distance, min_delay, anchors_gps[anchor][0], anchors_gps[anchor][1], radi))
        if len(points) == 0:
            logging.debug("no valid pings results")
            return []
        return points

    def is_valid(self, results):
        """
        Need reasonable threshold to answer the validation of location
        For now, we say it is valid if 90% of 30 nearest anchors are True
        """
        total = 0
        count_valid = 0
        limit = 30
        for valid, aux in results:
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