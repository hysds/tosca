import os, json, requests, base64, io
from collections import OrderedDict
from flask import jsonify, Blueprint, request, url_for, Response, render_template, make_response
from flask_login import login_required
from flask_cors import CORS, cross_origin
from pprint import pformat
from datetime import datetime

from tosca import app


mod = Blueprint('services/wget', __name__)


#@mod.route('/wget/<dataset>', methods=['GET'])
@mod.route('/wget', methods=['GET'])
@login_required
def get_wget(dataset=None):
    """Return wget for dataset."""

    # get callback, source, and dataset
    print(request.args.get('source'))
    print(request.args)
    print(request.args.to_dict(flat=False)['queryParam'][0])
    #print(request.get(queryParam))
    #print(request.get_json())
    #jsonData = request.get_json()
    #print(jsonData)
    print(dataset)
    source_b64 = request.args.get('base64')
    source = request.args.get('source')
    if source_b64 is not None:
        source = base64.b64decode(source_b64)
    if dataset is None:
        return jsonify({
            'success': False,
            'message': "Cannot recognize dataset: %s" % dataset,
        }), 500

    app.logger.info("source: {}".format(source))
    app.logger.info("source_b64: {}".format(source_b64))

    # query
    es_url = app.config['ES_URL']
    index = dataset
    r = requests.post('%s/%s/_search?search_type=scan&scroll=10m&size=100' % (es_url, index), data=source)
    if r.status_code != 200:
        app.logger.debug("Failed to query ES. Got status code %d:\n%s" %
                         (r.status_code, json.dumps(result, indent=2)))
    r.raise_for_status()
    #app.logger.debug("result: %s" % pformat(r.json()))

    scan_result = r.json()
    count = scan_result['hits']['total']
    scroll_id = scan_result['_scroll_id']

    # fields
    fields = OrderedDict([ ('starttime', 'starttime'),
                           ('endtime', 'endtime'),
                           ('status', 'metadata.status'),
                           ('platform', 'metadata.platform'),
                           ('sensor', 'metadata.instrumentshortname'),
                           ('orbit', 'metadata.orbitNumber'),
                           ('track', 'metadata.trackNumber'),
                           ('mode', 'metadata.sensoroperationalmode'),
                           ('direction', 'metadata.direction'),
                           ('polarisation', 'metadata.polarisationmode'),
                           ('dataset_id', 'id'),
                         ])

    # stream output a page at a time for better performance and lower memory footprint
    def stream_csv(scroll_id, source):
        yield "{}\n".format(','.join(fields))

        while True:
            r = requests.post('%s/_search/scroll?scroll=10m' % es_url, data=scroll_id)
            res = r.json()
            #app.logger.debug("res: %s" % pformat(res))
            scroll_id = res['_scroll_id']
            if len(res['hits']['hits']) == 0: break
            # Elastic Search seems like it's returning duplicate urls. Remove duplicates
            unique_urls=[]
            for hit in res['hits']['hits']:
                vals = []
                for field in fields:
                    es_field = fields[field]
                    if '.' in es_field:
                        f1, f2 = es_field.split('.')
                        vals.append(hit['_source'][f1][f2])
                    else: vals.append(hit['_source'][es_field])
                yield "{}\n".format(','.join(map(str, vals)))

    fname = "sar_availability-acquisitions-{}.csv".format(datetime.utcnow().strftime('%Y%m%dT%H%M%S'))
    headers = {'Content-Disposition': 'attachment; filename={}'.format(fname)}
    return Response(stream_csv(scroll_id, source), headers=headers, mimetype="text/csv")


def pull_all_data_sets(es_url, query):
    batch_size = 1000
    query['fields'] = ['_id', 'metadata.archive_filename']

    from pprint import pprint
    def pull_es_data(start):
        query['from'] = start
        query['size'] = batch_size

        req = requests.post(es_url, data=json.dumps(query), verify=False)
        if req.status_code != 200:
            raise "Elasticsearch went wrong"
        es_results = req.json()
        return [row['fields']['metadata.archive_filename'][0] for row in  es_results["hits"]["hits"] if row['fields'].get('metadata.archive_filename')]

    data_sets = []
    pagination = 0
    while True:
        batch = pull_es_data(pagination)
        if len(batch) == 0:
            break
        data_sets += batch
        pagination += batch_size
    return data_sets


@mod.route('/wget_all/<dataset>', methods=['GET'])
@cross_origin(origin='*')
@login_required
def get_wget_all(dataset):
    """Return wget for dataset."""
    source_b64 = base64.b64decode(dataset)
    if source_b64 is not None:
        source = base64.b64decode(dataset)
        source = json.loads(source)  # this is the es query
        app.logger.info("source: {}".format(source))
        app.logger.info("source_b64: {}".format(source_b64))
    else:
        return jsonify({
            'success': False,
            'message': "Cannot recognize dataset: %s" % dataset,
        }), 500

    es_url_base = app.config['ES_URL']
    index = 'grq_v2.0.1_s1-gunw'
    es_url = "%s/%s/_search" % (es_url_base, index)

    f = io.BytesIO()
    f.write('# !/bin/bash\n'.encode('utf-8'))
    f.write('#\n'.encode('utf-8'))
    f.write('# download script generated from query:\n'.encode('utf-8'))
    f.write(('# ' + json.dumps(source) + '\n').encode('utf-8'))

    all_products = pull_all_data_sets(es_url, source)
    f.write(('# total datasets matched: %i \n' % len(all_products)).encode('utf-8'))
    f.write('#\n'.encode('utf-8'))

    wget_template = "wget --no-clobber --load-cookies /tmp/cookies.txt --save-cookies /tmp/cookies.txt --keep-session-cookies https://grfn.asf.alaska.edu/door/download/{}\n"
    for product in all_products:
        line = wget_template.format(product)
        f.write(line.encode('utf-8'))

    fname = "standard_products-{}.sh".format(datetime.utcnow().strftime('%Y%m%dT%H%M%S'))
    output = make_response(f.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename={}".format(fname)
    output.headers["Content-type"] = "text"
    return output
