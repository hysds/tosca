import json, requests, types, re, io
from flask import jsonify, Blueprint, request, Response, render_template, make_response
from flask_login import login_required
from flask_cors import CORS, cross_origin
from pprint import pformat

from tosca import app

import boto3
from urlparse import urlparse

mod = Blueprint('services/wget', __name__)


def format_source(src):
    """Format source query as commented text."""

    j = json.loads(src)
    fmt_src = ""
    for i in json.dumps(j, indent=2).split('\n'):
        fmt_src += "#%s\n" % i
    return fmt_src


@mod.route('/wget_script/<dataset>', methods=['GET'])
@login_required
def wget_script(dataset=None):
    """Return wget script."""

    # get callback, source, and dataset
    source = request.args.get('source')
    if dataset is None:
        return jsonify({
            'success': False,
            'message': "Cannot recognize dataset: %s" % dataset,
        }), 500

    # rebuild query without facets
    #app.logger.debug("ES query for wget_script(): %s" % source)
    src = json.loads(source)
    #app.logger.debug("ES src for wget_script(): %s" % json.dumps(src, indent=2))
    new_src = {}
    for k in src:
        if k != "facets": new_src[k] = src[k]
    #app.logger.debug("ES new_src for wget_script(): %s" % json.dumps(new_src, indent=2))

    # query
    es_url = app.config['ES_URL']
    index = dataset
    r = requests.post('%s/%s/_search?search_type=scan&scroll=10m&size=100' % (es_url, index), data=json.dumps(new_src))
    if r.status_code != 200:
        app.logger.debug("Failed to query ES. Got status code %d:\n%s" % 
                         (r.status_code, json.dumps(r.json(), indent=2)))
    r.raise_for_status()
    #app.logger.debug("result: %s" % pformat(r.json()))

    scan_result = r.json()
    count = scan_result['hits']['total']
    scroll_id = scan_result['_scroll_id']

    # stream output a page at a time for better performance and lower memory footprint
    def stream_wget(scroll_id, source):
        formatted_source = format_source(source)
        yield '#!/bin/bash\n#\n' + \
              '# query:\n#\n' + \
              '%s#\n#\n' % formatted_source + \
              '# total datasets matched: %d\n\n' % count + \
              'read -s -p "JPL Username: " user\n' + \
              'echo ""\n' + \
              'read -s -p "JPL Password: " password\n' + \
              'echo ""\n'
        wget_cmd = 'wget --no-check-certificate --mirror -np -nH --reject "index.html*"'
        wget_cmd_password = wget_cmd + ' --user=$user --password=$password'

        while True:
            r = requests.post('%s/_search/scroll?scroll=10m' % es_url, data=scroll_id)
            res = r.json()
            #app.logger.debug("res: %s" % pformat(res))
            scroll_id = res['_scroll_id']
            if len(res['hits']['hits']) == 0: break
	    # Elastic Search seems like it's returning duplicate urls. Remove duplicates
	    unique_urls=[]
            for hit in res['hits']['hits']:
		[unique_urls.append(url) for url in hit['_source']['urls'] if url not in unique_urls]
	    
	    for url in unique_urls:
		if 'hysds-aria-products.s3-website' in url:
			parsed_url = urlparse(url)
			cut_dirs = len(parsed_url.path[1:].split('/')) - 1
		else:
			if 's1a_ifg' in url:
				cut_dirs = 3
			else:
				cut_dirs = 6
		if 'hysds-aria-products.s3-website' in url:
                        files = get_s3_files(url)
			for file in files:
				yield 'echo "downloading  %s"\n' % file
				if 's1a_ifg' in url:
					yield "%s --cut-dirs=%d %s\n" % (wget_cmd, cut_dirs, file)
				else:
					yield "%s --cut-dirs=%d %s\n" % (wget_cmd, cut_dirs, file)
                if 'aria-dav.jpl.nasa.gov' in url:
			yield 'echo "downloading  %s"\n' % url
                        yield "%s --cut-dirs=%d %s/\n" % (wget_cmd_password, (cut_dirs+1), url)
                if 'aria-csk-dav.jpl.nasa.gov' in url:
			yield 'echo "downloading  %s"\n' % url
                        yield "%s --cut-dirs=%d %s/\n" % (wget_cmd_password, (cut_dirs+1), url)
                if 'aria-dst-dav.jpl.nasa.gov' in url:
			yield 'echo "downloading  %s"\n' % url
                        yield "%s --cut-dirs=%d %s/\n" % (wget_cmd, cut_dirs, url)
                        break

    headers = {'Content-Disposition': 'attachment; filename=wget.sh'}
    return Response(stream_wget(scroll_id, source), headers=headers, mimetype="text/plain") 

def get_s3_files(url):
	files = []
	parsed_url = urlparse(url)
        bucket = parsed_url.hostname.split('.', 1)[0]
 	client = boto3.client('s3')
	results = client.list_objects(Bucket=bucket, Delimiter='/', Prefix=parsed_url.path[1:] + '/')
        
	if results.get('Contents'):
		for result in results.get('Contents'):
			files.append(parsed_url.scheme + "://" + parsed_url.hostname + '/' + result.get('Key'))
	
	if results.get('CommonPrefixes'):
		for result in results.get('CommonPrefixes'):
			# Prefix values have a trailing '/'. Let's remove it to be consistent with our dir urls
			folder = parsed_url.scheme + "://" + parsed_url.hostname + '/' + result.get('Prefix')[:-1]
			files.extend(get_s3_files(folder))
	return files


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

