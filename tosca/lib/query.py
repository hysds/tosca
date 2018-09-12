import json, requests, re
from pprint import pformat
from flask import url_for
from urllib import quote_plus

from tosca import app


DAP_RE = re.compile(r'^http.*/(dap|dods|opendap|thredds)/')


def query(index, query_str):
    """Query ElasticSearch."""

    # query
    es_url = app.config['ES_URL']
    #app.logger.debug("ES query for query(): %s" % json.dumps(json.loads(query_str), indent=2))
    r = requests.post('%s/%s/_search' % (es_url, index), data=query_str)
    result = r.json()
    if r.status_code != 200:
        app.logger.debug("Failed to query ES. Got status code %d:\n%s" % 
                         (r.status_code, json.dumps(result, indent=2)))
    r.raise_for_status()
    #app.logger.debug("result: %s" % pformat(r.json()))

    # return only one url
    for hit in result['hits']['hits']:
        # emulate result format from ElasticSearch <1.0
        #app.logger.debug("hit: %s" % pformat(hit))
        if '_source' in hit: hit.setdefault('fields', {}).update(hit['_source'])
        hit['fields']['es_index'] = hit['_index']

        # set dap url
        set_dap_url(hit)

        # set browse url
        set_browse_url(hit)

        # set redirector url
        if len(hit['fields']['urls']) == 0:
            hit['fields']['urls'] = None
        else: hit['fields']['urls'] = [ url_for('services/dataset.resolve_url',
                                                index=hit['_index'], id=hit['_id']) ]

        # set closest city
        if len(hit['fields'].get('city', [])) > 0:
            hit['fields']['city'] = hit['fields']['city'][0]

    return result


def query_dataset_url(index, objectid):
    """Query ElasticSearch index for dataset url."""

    # query
    es_url = app.config['ES_URL']
    query_url = "%s/%s/_all/%s" % (es_url, index, quote_plus(objectid))
    #r = requests.get("%s/%s/_all/%s" % (es_url, index, objectid))
    r = requests.get(query_url)
    #app.logger.debug("url: %s" % r.url)
    result = r.json()
    if r.status_code != 200:
        app.logger.debug("Failed to query ES. Got status code %d:\n%s" % 
                         (r.status_code, json.dumps(result, indent=2)))
    r.raise_for_status()
    #app.logger.info("result: %s" % json.dumps(result, indent=2))

    # get dataset url
    return get_dataset_url(result).replace('+', '%2B')


def set_dap_url(hit):
    """Select OpenDAP url."""

    for url in hit['fields']['urls']:
        if DAP_RE.search(url):
            hit['fields']['dap_url'] = [url]


def set_browse_url(hit):
    """Select browse image url."""

    for url in hit['fields']['browse_urls']:
        if url.startswith('http') and 'amazonaws.com' in url:
            hit['fields']['browse_urls'] = [url]
            return
        if url.startswith('http') and 'googleapis.com' in url:
            hit['fields']['browse_urls'] = [url]
            return
        if url.startswith('http'):
            hit['fields']['browse_urls'] = [url]
            return


def get_dataset_url(hit):
    """Select dataset url."""

    ret_url = None
    for url in hit['_source'].get('urls', []):
        if url.startswith('http'): ret_url = url
        if url.startswith('http') and 'amazonaws.com' in url: ret_url = url
        if url.startswith('http') and 'googleapis.com' in url: ret_url = url
    return ret_url
