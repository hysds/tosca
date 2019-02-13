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
    if dataset is None:
        return jsonify({
            'success': False,
            'message': "Dataset not specified."
        }), 500

    # query
    result = query_es(dataset, source)

    # return JSONP
    return Response('%s(%s)' % (callback, json.dumps(result)),
                    mimetype="application/javascript")
