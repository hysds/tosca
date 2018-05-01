import json
from requests import HTTPError
from flask import Blueprint, redirect, abort, request
from flask_login import login_required

from tosca import app
from tosca.lib.query import query_dataset_url


mod = Blueprint('services/dataset', __name__)


@mod.route('/dataset/<index>/<id>', methods=['GET'])
@mod.route('/dataset/<index>/<id>/<path:path>', methods=['GET'])
def resolve_url(index=None, id=None, path=None):
    """Query interface for FacetView."""

    # check args
    if index is None:
        abort(500, "No dataset specified.")
    if id is None:
        abort(500, "No dataset ID specified.")

    # query
    err = "Unable to find dataset %s in index %s." % (id, index)
    try: url = query_dataset_url(index, id)
    except HTTPError, e:
        if e.response.status_code == 404: abort(404, err)
        else: raise(e)
    if url is None: abort(500, err)

    # check if noredirect is set; if so just return url
    noredirect = request.args.get('noredirect', "false")
    if noredirect in ('true', 'True', 'TRUE'): return url

    # redirect
    if path is None: return redirect(url)
    else: return redirect("%s/%s" % (url, path))
