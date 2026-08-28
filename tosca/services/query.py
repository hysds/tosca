from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
import json
import requests
from flask import jsonify, Blueprint, request, Response, render_template, make_response
from flask_login import login_required

from tosca import app
from tosca.lib.query import query as query_es


mod = Blueprint('services/query', __name__)


@mod.route('/query/<dataset>', methods=['GET'])
@login_required
def query(dataset=None):
    """Query interface for FacetView."""

    # get callback, source
    callback = request.args.get('callback')
    source = request.args.get('source')

    def respond(payload, status=200):
        """Return JSONP when a callback was requested (legacy mapview clients),
        otherwise plain JSON. JSONP responses must be HTTP 200 so the browser
        executes the script and the caller sees the error payload."""

        if callback:
            return Response('%s(%s)' % (callback, json.dumps(payload)),
                            mimetype="application/javascript")
        return jsonify(payload), status

    if dataset is None:
        return respond({
            'success': False,
            'message': "Dataset not specified."
        }, 500)

    # query
    try:
        result = query_es(dataset, source)
    except Exception as e:
        app.logger.exception("Failed to query ES for FacetView.")
        return respond({
            'success': False,
            'message': "Failed to query Elasticsearch: %s" % str(e)
        }, 502)

    return respond(result)
