from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library

standard_library.install_aliases()
import os
import json
import requests
import math
import re
import hashlib
from datetime import datetime
import dateutil.parser
from flask import jsonify, Blueprint, request, url_for, Response
from flask_login import login_required
from pprint import pformat
import base64
import simplekml
from tosca import app

mod = Blueprint("services/kml", __name__)


@mod.route("/services/kml/<dataset>", methods=["GET"])
def get_kml(dataset=None):
    """Return kml for dataset."""

    # get callback, source, and dataset
    source_b64 = request.args.get("base64")
    source = request.args.get("source")
    if source_b64 is not None:
        source = base64.b64decode(source_b64)
    if dataset is None:
        return (
            jsonify(
                {"success": False, "message": "Cannot recognize dataset: %s" % dataset,}
            ),
            500,
        )

    app.logger.info("source: {}".format(source))
    app.logger.info("source_b64: {}".format(source_b64))

    # query
    decoded_query = json.loads(source)
    results = get_es_results(query=decoded_query)

    # build kml
    kml_obj = gen_kml(results)

    # return result
    fname = "sar_availability-acquisitions-{}.kml".format(
        datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    )
    return Response(
        kml_obj,
        headers={
            "Content-Type": "application/vnd.google-earth.kml+xml",
            "Content-Disposition": "attachment; filename={}".format(fname),
        },
    )


def gen_poly(kmlobj, acq):
    """Create a new polygon for the KML for an acquisition"""
    # generate params from acquisition
    prm = gen_acq_dict(acq)
    # save the params as a polygon
    pol = kmlobj.newpolygon(name=prm["name"])
    pol.outerboundaryis = prm["coord"]
    pol.timespan.begin = prm["starttime"]
    pol.timespan.end = prm["endtime"]
    pol.style.linestyle.color = gen_color(acq)
    pol.style.linestyle.width = 1
    pol.style.polystyle.color = simplekml.Color.changealphaint(100, gen_color(acq))
    pol.description = gen_kml_bubble(prm)


def gen_acq_dict(acq):
    """returns a dict of acquisition metadata & handles both ESA & BOS SARCAT datatypes"""
    uid = re.sub("\_+", "_", acq["_id"])
    coordinates = acq["_source"]["location"]["coordinates"][0]
    coord = convert_coord(coordinates)
    platform = walk(acq, "platform")
    download_url = walk(acq, "download_url")
    name = walk(acq, "title")
    if name:
        name = re.sub("\_+", "_", name)
    if name is None:
        name = (
            uid.replace("-bos_sarcat-predicted", "")
            .replace("-", "_")
            .replace("acquisition_", "")
            .replace("Sentinel_1", "S1")
        )
    start = walk(acq, "starttime")
    end = walk(acq, "endtime")
    source = walk(acq, "source")
    starttime = dateutil.parser.parse(start).strftime("%Y-%m-%d")
    endtime = dateutil.parser.parse(end).strftime("%Y-%m-%d")
    if dateutil.parser.parse(start) > dateutil.parser.parse(end):
        end = start
        endtime = starttime
    track = walk(acq, "track_number")
    location = walk(acq, "continent")
    status = walk(acq, "status")
    if status:
        status.replace("\n", "")
    center = walk(acq, "center")
    center_str = None
    if center:
        center_str = "{:.1f}, {:.1f}".format(
            center["coordinates"][1], center["coordinates"][0]
        )
    location = get_loc_string(acq)
    orbitnum = walk(acq, "orbitNumber")
    dct = {
        "uid": uid,
        "coord": coord,
        "coordinates": coordinates,
        "start": start,
        "end": end,
        "starttime": starttime,
        "endtime": endtime,
        "track": track,
        "source": source,
        "platform": platform,
        "orbitnum": orbitnum,
        "name": name,
        "download_url": download_url,
        "center": center_str,
        "location": location,
        "status": status,
    }
    return dct


def gen_color(acq):
    """returns color based on acquisition source"""
    platform = walk(acq, "platform")
    if platform is None:
        return simplekml.Color.blue
    platform = platform.lower()
    if platform.find("sentinel") != -1:
        return simplekml.Color.white
    elif platform.find("alos") != -1:
        return simplekml.Color.green
    elif platform.find("csk") != -1:
        return simplekml.Color.blue
    elif platform.find("radarsat") != -1:
        return simplekml.Color.red
    return convert_str_to_color(platform)


def convert_str_to_color(instr):
    """converts an input string into simplekml color deterministically"""
    hexstr = hashlib.md5(instr).hexdigest()
    r = int(hexstr[0], 16) * int(hexstr[1], 16)
    g = int(hexstr[2], 16) * int(hexstr[3], 16)
    b = int(hexstr[4], 16) * int(hexstr[5], 16)
    d = 255 - max([r, g, b])
    r += d
    g += d
    b += d
    return simplekml.Color.rgb(r, g, b)


def get_loc_string(acq):
    """determines the location from the acquisition metadata and returns it as a string"""
    city_list = walk(acq, "city")
    center = walk(acq, "center")
    lat = center["coordinates"][1]
    lon = center["coordinates"][0]
    center = [float(lon), float(lat)]
    loc_str = None
    distance = None
    for item in city_list:
        city_point = [float(item["longitude"]), float(item["latitude"])]
        cur_dist = get_distance(center, city_point)
        if loc_str is None:
            distance = cur_dist
            # build region
            if item["admin2_name"]:
                loc_str = build_loc_name(item)
        else:
            if cur_dist < distance:
                # build region
                loc_str = build_loc_name(item)
    return loc_str


def build_loc_name(item):
    """builds the location name from the item"""
    local = "" if item["admin2_name"] is None else item["admin2_name"]
    region = "" if item["admin1_name"] is None else item["admin1_name"]
    country = "" if item["country_name"] is None else item["country_name"]
    loc_str = ""
    if local:
        loc_str = "{}, {}, {}".format(
            local.encode("ascii", "ignore"),
            region.encode("ascii", "ignore"),
            country.encode("ascii", "ignore"),
        )
    else:
        loc_str = "{}, {}".format(
            region.encode("ascii", "ignore"), country.encode("ascii", "ignore")
        )
    return loc_str


def get_distance(point1, point2):
    """returns the distance between the two points in kilometers"""
    distance = (
        math.acos(
            math.sin(math.radians(point1[1])) * math.sin(math.radians(point2[1]))
            + math.cos(math.radians(point1[1]))
            * math.cos(math.radians(point2[1]))
            * math.cos(math.radians(point2[0]) - math.radians(point1[0]))
        )
        * 6371
    )
    return distance


def gen_kml_bubble(dct):
    """generates the html for the kml polygon"""
    lst = [
        "name",
        "platform",
        "location",
        "start",
        "end",
        "source",
        "track",
        "orbitnum",
        "coordinates",
        "uid",
        "status",
        "download_url",
    ]
    outstr = "<table>"
    for item in lst:
        if dct[item]:
            if item == "download_url":
                outstr += '<tr><td><b><font color=blue>{}</font></b></td><td> <a href="{}">{}</a></td></tr>'.format(
                    item.capitalize(), dct[item], dct[item]
                )
            else:
                outstr += "<tr><td><b><font color=blue>{}</font></b></td><td>{}</td></tr>".format(
                    item.capitalize(), dct[item]
                )
    return outstr + "</table>"


def convert_coord(es_coord):
    """gen coords for kml"""
    coord = []
    for point in es_coord:
        coord.append((str(point[0]), str(point[1])))
    return coord


def gen_kml(acquisitions_list, verbose=False):
    """Create a KML file showing acquisition coverage"""
    kmlobj = simplekml.Kml()
    for acquisition in acquisitions_list:
        gen_poly(kmlobj, acquisition)
    return kmlobj.kml()


def query_es(query, url):
    """query elastic search"""
    iterator_size = query["size"] = 2000  # override input query size
    data = json.dumps(query, indent=2)
    response = requests.get(url, data=data, verify=False, timeout=15)
    response.raise_for_status()
    results = json.loads(response.text, encoding="ascii")
    results_list = results["hits"]["hits"]
    total_results = int(results["hits"]["total"])
    if total_results > iterator_size:
        for i in range(iterator_size, total_results, iterator_size):
            query["from"] = i
            response = requests.get(url, data=data, verify=False, timeout=15)
            response.raise_for_status()
            results = json.loads(response.text, encoding="ascii")
            results_list.extend(results["hits"]["hits"])
    return results_list


def walk(node, key_match):
    """recursive node walk, returns None if nothing found, returns the value if a key matches key_match"""
    if isinstance(node, dict):
        for key, item in node.items():
            # print('searching {} for {}'.format(key, key_match))
            if str(key) == str(key_match):
                # print('found {}: {}'.format(key, item))
                return item
            result = walk(item, key_match)
            if not result is None:
                return result
        return None
    if isinstance(node, list):
        for item in node:
            if isinstance(item, dict) or isinstance(item, list):
                result = walk(item, key_match)
                if not result is None:
                    return result
        return None
    return None


def get_es_results(query=None, source="bos", verbose=False):
    """get the elasticsearch results from the given query"""
    index = "grq_*_acquisition-*"
    grq_ip = app.config["ES_URL"]
    url = "{}/{}/_search".format(grq_ip, index)
    # run the es query & return the results
    if verbose:
        print("query: {}".format(query))
    results = query_es(query, url)
    return results
