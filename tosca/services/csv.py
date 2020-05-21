import os, json, requests, base64
from collections import OrderedDict
from flask import jsonify, Blueprint, request, url_for, Response
from flask_login import login_required
from pprint import pformat
from datetime import datetime

from tosca import app


mod = Blueprint("services/csv", __name__)


@mod.route("/services/csv/<dataset>", methods=["GET"])
def get_csv(dataset=None):
    """Return csv for dataset."""

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
        app.logger.debug(
            "Failed to query ES. Got status code %d:\n%s"
            % (r.status_code, json.dumps(result, indent=2))
        )
    r.raise_for_status()
    # app.logger.debug("result: %s" % pformat(r.json()))

    scan_result = r.json()
    count = scan_result["hits"]["total"]
    scroll_id = scan_result["_scroll_id"]

    # fields
    fields = OrderedDict(
        [
            ("starttime", "starttime"),
            ("endtime", "endtime"),
            ("status", "metadata.status"),
            ("platform", "metadata.platform"),
            ("sensor", "metadata.instrumentshortname"),
            ("orbit", "metadata.orbitNumber"),
            ("track", "metadata.track_number"),
            ("mode", "metadata.sensoroperationalmode"),
            ("direction", "metadata.direction"),
            ("polarisation", "metadata.polarisationmode"),
            ("dataset_id", "id"),
        ]
    )

    # stream output a page at a time for better performance and lower memory footprint
    def stream_csv(scroll_id, source):
        yield "{}\n".format(",".join(fields))

        while True:
            r = requests.post("%s/_search/scroll?scroll=10m" % es_url, data=scroll_id)
            res = r.json()
            # app.logger.debug("res: %s" % pformat(res))
            scroll_id = res["_scroll_id"]
            if len(res["hits"]["hits"]) == 0:
                break
            # Elastic Search seems like it's returning duplicate urls. Remove duplicates
            unique_urls = []
            for hit in res["hits"]["hits"]:
                vals = []
                for field in fields:
                    es_field = fields[field]
                    if "." in es_field:
                        f1, f2 = es_field.split(".")
                        vals.append(hit["_source"][f1][f2])
                    else:
                        vals.append(hit["_source"][es_field])
                yield "{}\n".format(",".join(map(str, vals)))

    fname = "sar_availability-acquisitions-{}.csv".format(
        datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    )
    headers = {"Content-Disposition": "attachment; filename={}".format(fname)}
    return Response(stream_csv(scroll_id, source), headers=headers, mimetype="text/csv")
