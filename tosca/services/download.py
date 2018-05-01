import os, json, requests, types, re, hashlib, shutil, subprocess
from flask import jsonify, Blueprint, request, url_for
from flask_login import login_required
from pprint import pformat
from urlparse import urlparse

from tosca import app


mod = Blueprint('services/download', __name__)


@mod.route('/services/download/<dataset>', methods=['GET'])
@login_required
def download(dataset=None):
    """Return downloaded tarball."""

    # get callback, source, and dataset
    source = request.args.get('source')
    if dataset is None:
        return jsonify({
            'success': False,
            'message': "Cannot recognize dataset: %s" % dataset,
        }), 500

    # query
    es_url = app.config['ES_URL']
    index = dataset
    app.logger.debug("ES query for download(): %s" % source)
    r = requests.post('%s/%s/_search?search_type=scan&scroll=10m&size=100' % (es_url, index), data=source)
    if r.status_code != 200:
        app.logger.debug("Failed to query ES. Got status code %d:\n%s" % 
                         (r.status_code, json.dumps(result, indent=2)))
    r.raise_for_status()
    #app.logger.debug("result: %s" % pformat(r.json()))

    scan_result = r.json()
    count = scan_result['hits']['total']
    scroll_id = scan_result['_scroll_id']

    # get list of urls
    urls = []
    while True:
        r = requests.post('%s/_search/scroll?scroll=10m' % es_url, data=scroll_id)
        res = r.json()
        scroll_id = res['_scroll_id']
        if len(res['hits']['hits']) == 0: break
        for hit in res['hits']['hits']:
            # emulate result format from ElasticSearch <1.0
            if '_source' in hit: hit['fields'].update(hit['_source'])
            if len(hit['fields']['urls']) > 0: urls.append(hit['fields']['urls'][0])

    # generate tarball
    urls.sort()
    m = hashlib.md5()
    m.update(json.dumps(urls))
    digest = m.hexdigest()
    sync_dir = os.path.join(app.config['SCRATCH_DIR'], 'data')
    if not os.path.exists(sync_dir): os.makedirs(sync_dir)
    dl_dir = os.path.join(app.config['SCRATCH_DIR'], 'downloads', digest, 'download')
    if not os.path.exists(dl_dir): os.makedirs(dl_dir)
    tar_file_path = os.path.join(app.config['SCRATCH_DIR'], 'downloads', digest, '%s.tbz2' % digest)
    if not os.path.exists(tar_file_path):
        for i, f in enumerate(urls):
            p = urlparse(f)
            cut_dirs = p.path.count('/') - 1
            prod_name = os.path.basename(p.path)
            src_dir = os.path.join(sync_dir, prod_name)
            if not os.path.exists(src_dir):
                cmd = 'wget --no-check-certificate -P %s ' % sync_dir
                cmd += '--mirror -nv -np -nH --reject "index.html*" '
                cmd += '--user=pucops --password=puc_0ps --cut-dirs=%s %s' % (cut_dirs, f)
                sts = subprocess.call(cmd, shell=True)
            src_dir = os.path.join(sync_dir, prod_name)
            dest_dir = os.path.join(dl_dir, prod_name)
            if not os.path.exists(dest_dir): os.symlink(src_dir, dest_dir)
        sts = subprocess.call('tar cfhj %s %s' % (tar_file_path, dl_dir), shell=True)

    return jsonify({
        'success': True,
        'message': "",
        'url': os.path.join(app.config['SCRATCH_URL'],
                            os.path.relpath(tar_file_path, app.config['SCRATCH_DIR']))
    })
