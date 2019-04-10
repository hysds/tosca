import os, json, requests, base64, io
from collections import OrderedDict
from flask import jsonify, Blueprint, request, url_for, Response, make_response
from flask_login import login_required
from flask_cors import CORS, cross_origin
from pprint import pformat
from datetime import datetime

from tosca import app


mod = Blueprint('services/wget', __name__)



def pull_all_data_sets(es_url, query):
    batch_size = 1000
    query['fields'] = ['_id']

    def pull_es_data(start):
        query['from'] = start
        query['size'] = batch_size

        req = requests.post(es_url, data=json.dumps(query), verify=False)
        if req.status_code != 200:
            raise "Elasticsearch went wrong"
        es_results = req.json()
        return [row["_id"] for row in es_results["hits"]["hits"]]

    data_sets = []
    pagination = 0
    while True:
        batch = pull_es_data(pagination)
        if len(batch) == 0:
            break
        data_sets += batch
        pagination += batch_size
    return data_sets


@mod.route('/wget/<dataset>', methods=['GET'])
@cross_origin(origin='*')
@login_required
def get_wget(dataset):
    """Return wget for dataset."""
    source_b64 = base64.b64decode(dataset)
    if source_b64 is not None:
        source = base64.b64decode(dataset)
        source = json.loads(source)  # this is the es query
    else:
        return jsonify({
            'success': False,
            'message': "Cannot recognize dataset: %s" % dataset,
        }), 500

    es_url_base = app.config['ES_URL']
    index = 'grq_v2.0.0_s1-gunw-merged'
    #es_url = '%s/%s/_search?search_type=scan&scroll=10m&size=100' % (es_url, index)
    es_url = "%s/%s/_search" % (es_url_base, index)
    
    #r = requests.post(es_url, data=json.dumps(source))
    all_products = pull_all_data_sets(es_url, source)

    f = io.BytesIO()
    wget_template = "wget --load-cookies /tmp/cookies.txt --save-cookies /tmp/cookies.txt --keep-session-cookies https://grfn.asf.alaska.edu/door/download/{}.nc\n"
    for product in all_products:
        line = wget_template.format(product)
        f.write(line.encode('utf-8'))

    fname = "standard_products-{}.sh".format(datetime.utcnow().strftime('%Y%m%dT%H%M%S'))
    output = make_response(f.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename={}".format(fname)
    output.headers["Content-type"] = "text"
    return output

