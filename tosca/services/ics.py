import os, json, requests, base64, re, math
from datetime import datetime
from flask import jsonify, Blueprint, request, url_for, Response
from flask_login import login_required
from pprint import pformat
from icalendar import Calendar, Event, vCalAddress, vText
import simplekml
import dateutil
import hashlib

from tosca import app


mod = Blueprint("services/ics", __name__)


def gen_poly(kmlobj, acq):
    """Create a new polygon for the KML for an acquisition"""
    # generate params from acquisition
    prm = gen_acq_dict(acq)
    # save the params as a polygon
    pol = kmlobj.newpolygon(name=prm["name"])
    pol.outerboundaryis = prm["coord"]
    # pol.innerboundaryis = coord
    pol.timespan.begin = prm["starttime"]
    pol.timespan.end = prm["endtime"]
    pol.style.linestyle.color = gen_color(acq)
    pol.style.linestyle.width = 1
    pol.style.polystyle.color = simplekml.Color.changealphaint(100, gen_color(acq))
    pol.description = gen_kml_bubble(prm)


def gen_acq_dict(acq):
    """returns a dict of acquisition metadata & handles both ESA & BOS SARCAT datatypes"""
    # app.logger.debug(json.dumps(acq, indent=2))
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
        # end = (dateutil.parser.parse(start) + datetime.timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
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
    # try:
    location = get_loc_string(acq)
    # except Exception, err:
    #    raise Exception(err)
    # name = acq['_source']['metadata']['title']
    # platform = acq['_source']['metadata']['platform']
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
            loc_str = build_loc_name(item)
        else:
            if cur_dist < distance:
                # build region & skip empty values
                loc_name = build_loc_name(item)
                if loc_name:
                    loc_str = loc_name
    return loc_str


def build_loc_name(item):
    """builds the location name from the item. Skip None values"""
    lst = [
        walk(item, "admin2_name"),
        walk(item, "admin1_name"),
        walk(item, "country_name"),
    ]
    regionlst = [x.encode("ascii", "ignore") for x in lst if x]
    return ", ".join(regionlst)


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


def gen_kml(acquisitions_list, verbose):
    """Create a KML file showing acquisition coverage"""
    kmlobj = simplekml.Kml()
    coord = None
    for acquisition in acquisitions_list:
        gen_poly(kmlobj, acquisition)
    return kmlobj.kml()


def gen_ics(results, verbose):
    # mail, AOI_name, acquisitions_list):
    """Create a vCal with acquisitions as events"""
    place = "event_response"
    cal = Calendar()
    cal.add("version", "2.0")
    organizer = vCalAddress("MAILTO:aria-help@jpl.nasa.gov")
    location = vText(place)
    acq_starttime = None
    acq_endtime = None
    for acq in results:
        dct = gen_acq_dict(acq)
        acquisition_id = "{name} ({status})".format(
            name=dct["name"], status=dct["status"]
        )
        acq_start = dateutil.parser.parse(dct["start"])  # .strftime("%Y%m%dT%H%M%S")
        acq_end = dateutil.parser.parse(dct["end"])  # .strftime("%Y%m%dT%H%M%S")
        sum_time = "{} - {}".format(
            acq_start.strftime("%H:%M.%S"), acq_end.strftime("%H:%M.%S")
        )
        summary = "{}\ntime: {} UTC\ntrack: {}\norbit: {}\nsource: {}\nlocation: {}\nstatus: {}\ndownload_url: {}".format(
            acquisition_id,
            sum_time,
            dct["track"],
            dct["orbitnum"],
            dct["source"],
            dct["coordinates"],
            dct["status"],
            dct["download_url"],
        )
        event = Event()
        event.add("dtstart", acq_start)
        event.add("dtend", acq_end)
        event.add("summary", acquisition_id)
        event.add("location", "{}: {}".format(dct["location"], dct["center"]))
        event.add("description", summary)
        event.add("organizer", organizer)
        event.add("priority", 8)
        event["uid"] = acquisition_id
        cal.add_component(event)
    cal_content = cal.to_ical()
    return cal_content


def query_es(query, url):
    """Query GRQ elastic search"""
    data = json.dumps(query, indent=2)
    req_result = requests.get(url, data=data)  # , verify=False, timeout=15)
    req_result.raise_for_status()
    return json.loads(req_result.text)


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
    # first we get relevant values of coordinates & datetimes (or AOI) from the input query
    location = walk(query, "location")
    starttime = walk(query, "starttime")
    endtime = walk(query, "endtime")
    if starttime != None and type(starttime) != str:
        endtime = starttime["to"]
        starttime = starttime["from"]
    # run using esa or bos
    if source == "bos":
        product = "acquisition-SARCAT"
        index = "grq_v0.2_acquisition-sarcat"
    elif source == "esa":
        product = "acquisition-S1-IW_SLC"
        index = "grq_v1.1_acquisition-s1-iw_slc"
    url = "http://localhost:9200/{}/_search".format(index)
    # TEMP WORKAROUND TO HIT B CLUSTER
    # url = 'http://{}/es/{}/_search'.format('100.64.134.208', index)
    if verbose:
        print(
            "using:\nstarttime: {}\nendtime: {}\nlocation: {}\n".format(
                starttime, endtime, location
            )
        )
    new_query = {
        "from": 0,
        "size": 10000,
        "query": {
            "filtered": {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"dataset.raw": product}},
                            {"range": {"starttime": {"gte": starttime}}},
                            {"range": {"endtime": {"lte": endtime}}},
                        ]
                    }
                },
                "filter": {"geo_shape": {"location": location}},
            }
        },
    }
    if endtime is None:
        del new_query["query"]["filtered"]["query"]["bool"]["must"][2]
    if starttime is None:
        del new_query["query"]["filtered"]["query"]["bool"]["must"][1]
    # now run the es query & return the results
    if verbose:
        print("query: {}".format(new_query))
    results = query_es(new_query, url)
    return results["hits"]["hits"]


def gen_product(product=None, results=None, verbose=False):
    """generate the stream of the given product type for the input results"""
    if product == "kml":
        return gen_kml(results, verbose)
    if product == "ics":
        return gen_ics(results, verbose)


def run_test():
    """run a test for the given product type"""
    # base64 = 'eyJxdWVyeSI6eyJmaWx0ZXJlZCI6eyJxdWVyeSI6eyJtYXRjaF9hbGwiOnt9fSwiZmlsdGVyIjp7Imdlb19zaGFwZSI6eyJsb2NhdGlvbiI6eyJzaGFwZSI6eyJ0eXBlIjoicG9seWdvbiIsImNvb3JkaW5hdGVzIjpbW1stNzguNzYyNDM4Nzc0MTgxNTYsNDAuMDYxODg3MTg5NTE5NjFdLFstODAuMTUwNjY2NTQzNDAwOTksMzguMzYzMTUxNzA4NTk0MDZdLFstODAuNDU0MzY0MDg2NTk2NCwzNy4yMTg1MTY1OTYyNjkxM10sWy03OS4yMzgwOTM5Mzg1ODk5NCwzNC40MDY1MDM5NjY1MTYwN10sWy04MS40OTU5ODIyMjc5NzEwNCwzMi40MDMzMDU1NDczODc4NV0sWy04MC41OTExNTM5MDI0NjEzNywzMS40MjI5OTAzMDUxNDQ2Ml0sWy03Ny44NzQzMDkwNDkwOTI2NywzMy40NjY3NjEwODE3Nzk1Ml0sWy03NS4xMzgyMjg2MjQzNDg3OCwzNS4wNTM4NjEzODY4MTY0XSxbLTc1LjY0NjMyMzYyOTAyNTAzLDM2Ljk0OTU5MDIyNDc4NjU4XSxbLTc0LjI2ODY5ODEyMDkxMTY4LDM4LjY2OTQ2NjQ0NTMyNTY1XSxbLTc2LjE3MjYwNTc0MDIzODY1LDM5LjYxODk0Nzk3MjUxOTQyXSxbLTc4Ljc2MjQzODc3NDE4MTU2LDQwLjA2MTg4NzE4OTUxOTYxXV1dfX19fX19LCJzb3J0IjpbeyJfdGltZXN0YW1wIjp7Im9yZGVyIjoiZGVzYyJ9fV0sImZpZWxkcyI6WyJfdGltZXN0YW1wIiwiX3NvdXJjZSJdfQ=='
    base64 = "eyJxdWVyeSI6eyJmaWx0ZXJlZCI6eyJxdWVyeSI6eyJib29sIjp7Im11c3QiOlt7InJhbmdlIjp7InN0YXJ0dGltZSI6eyJmcm9tIjoiMjAxOC0wOC0wMVQwMDowMDowMFoiLCJ0byI6IjIwMTgtMTEtMzBUMjM6NTk6NTlaIn19fV19fSwiZmlsdGVyIjp7Imdlb19zaGFwZSI6eyJsb2NhdGlvbiI6eyJzaGFwZSI6eyJ0eXBlIjoicG9seWdvbiIsImNvb3JkaW5hdGVzIjpbW1stNzYuNDUzOTQzMjUyNTYzNDgsMzguMjQ0NzE5MTA1MzE1MDU2XSxbLTc5LjEwNjYyNjUxMDYyMDEzLDM4LjE2ODg0NDIxODA5Nzc2XSxbLTgxLjM0OTAzOTA3Nzc1ODgsMzUuNDg2NTMyNjAwNDg0ODY0XSxbLTgyLjM5MTE5NTI5NzI0MTIzLDMzLjk5NTc1MDE1OTI1MTI1XSxbLTgwLjg5MDI3NDA0Nzg1MTU4LDMyLjA5OTQ0NDcyMDk5NjEwNF0sWy03Ni4yMDU0NjM0MDk0MjM4MywzNC45NzQ0NTQyNjA2MDM0Ml0sWy03NS4zMDkxMzM1Mjk2NjMxLDM2LjExMzA1NTM1MDMzNTMxXSxbLTc2LjQ1Mzk0MzI1MjU2MzQ4LDM4LjI0NDcxOTEwNTMxNTA1Nl1dXX19fX19fSwic2l6ZSI6OTAsInNvcnQiOlt7Il90aW1lc3RhbXAiOnsib3JkZXIiOiJkZXNjIn19XSwiZmllbGRzIjpbIl90aW1lc3RhbXAiLCJfc291cmNlIl19"
    return base64


@mod.route("/services/ics/<dataset>", methods=["GET"])
def get_ics(dataset=None):
    """Return ics for dataset."""

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
    es_url = app.config["ES_URL"]
    index = dataset
    r = requests.post(
        "%s/%s/_search?search_type=scan&scroll=10m&size=100" % (es_url, index),
        data=source,
    )
    if r.status_code != 200:
        result = r.json()
        app.logger.debug(
            "Failed to query ES. Got status code %d:\n%s"
            % (r.status_code, json.dumps(result, indent=2))
        )
    r.raise_for_status()
    # app.logger.debug("result: %s" % pformat(r.json()))

    scan_result = r.json()
    count = scan_result["hits"]["total"]
    scroll_id = scan_result["_scroll_id"]

    # get list of results
    results = []
    while True:
        r = requests.post("%s/_search/scroll?scroll=10m" % es_url, data=scroll_id)
        res = r.json()
        scroll_id = res["_scroll_id"]
        if len(res["hits"]["hits"]) == 0:
            break
        for hit in res["hits"]["hits"]:
            # del hit['_source']['city']
            results.append(hit)
    # app.logger.info("results: {}".format(json.dumps(results, indent=2)))

    cal = gen_product(product="ics", results=results, verbose=True)
    app.logger.info("cal: {}".format(cal))

    fname = "sar_availability-acquisitions-{}.ics".format(
        datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    )
    # return Response(cal, headers={'Content-Type': 'text/x-vcalendar',
    return Response(
        cal,
        headers={
            "Content-Type": "text/calendar",
            "Content-Disposition": "attachment; filename={}".format(fname),
        },
    )
