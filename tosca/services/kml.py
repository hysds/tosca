import os, json, requests
from flask import jsonify, Blueprint, request, url_for, Response
from flask_login import login_required
from pprint import pformat
import simplekml

from tosca import app


mod = Blueprint('services/kml', __name__)


@mod.route('/services/kml/<dataset>', methods=['GET'])
@login_required
def get_kml(dataset=None):
    """Return kml for dataset."""

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
    r = requests.post('%s/%s/_search?search_type=scan&scroll=10m&size=100' % (es_url, index), data=source)
    if r.status_code != 200:
        app.logger.debug("Failed to query ES. Got status code %d:\n%s" % 
                         (r.status_code, json.dumps(result, indent=2)))
    r.raise_for_status()
    #app.logger.debug("result: %s" % pformat(r.json()))

    scan_result = r.json()
    count = scan_result['hits']['total']
    scroll_id = scan_result['_scroll_id']

    # get list of results
    results = []
    while True:
        r = requests.post('%s/_search/scroll?scroll=10m' % es_url, data=scroll_id)
        res = r.json()
        scroll_id = res['_scroll_id']
        if len(res['hits']['hits']) == 0: break
        for hit in res['hits']['hits']:
            del hit['_source']['city']
            results.append(hit['_source'])

    # build kml
    kml = simplekml.Kml()
    kml.document.name = "Products Ingested by HySDS"
    kml.document.description
    for res in results:
        id = res['id']
        url = res['urls'][0] if len(res['urls']) > 0 else None
        browse_url = res['browse_urls'][0] if len(res['browse_urls']) > 0 else None
        location = res['location']
        bbox = res['metadata']['bbox']
        #app.logger.debug("%s" % json.dumps(res['metadata'], indent=2))
        img_coords = res['metadata'].get('imageCorners', {})
        if len(img_coords) == 0:
            if 'dfdn' in res['metadata']:
                if res['metadata']['direction'] == 'asc':
                    lowerleft  = res['metadata']['dfdn']['GeoCoordTopLeft']
                    lowerright = res['metadata']['dfdn']['GeoCoordTopRight']
                    upperleft  = res['metadata']['dfdn']['GeoCoordBottomLeft']
                    upperright = res['metadata']['dfdn']['GeoCoordBottomRight']
                else:
                    upperright  = res['metadata']['dfdn']['GeoCoordTopLeft']
                    upperleft = res['metadata']['dfdn']['GeoCoordTopRight']
                    lowerright  = res['metadata']['dfdn']['GeoCoordBottomLeft']
                    lowerleft = res['metadata']['dfdn']['GeoCoordBottomRight']
            else:
                #img_coords['minLon'] = bbox[2][1]
                #img_coords['maxLon'] = bbox[1][1]
                #img_coords['minLat'] = bbox[0][0]
                #img_coords['maxLat'] = bbox[3][0]
                #lowerleft  = [img_coords['minLat'], img_coords['minLon'], 0.]
                #lowerright = [img_coords['minLat'], img_coords['maxLon'], 0.]
                #upperright = [img_coords['maxLat'], img_coords['maxLon'], 0.]
                #upperleft  = [img_coords['maxLat'], img_coords['minLon'], 0.]
                lowerleft  = [bbox[0][0], bbox[0][1], 0.]
                lowerright  = [bbox[1][0], bbox[1][1], 0.]
                upperright  = [bbox[2][0], bbox[2][1], 0.]
                upperleft  = [bbox[3][0], bbox[3][1], 0.]
        else:
            lowerleft  = [img_coords['minLat'], img_coords['minLon'], 0.]
            lowerright = [img_coords['minLat'], img_coords['maxLon'], 0.]
            upperright = [img_coords['maxLat'], img_coords['maxLon'], 0.]
            upperleft  = [img_coords['maxLat'], img_coords['minLon'], 0.]
        ground = kml.newgroundoverlay(name=id)
        ground.description = id
        #if location['type'] == 'polygon':
        #    ground.gxlatlonquad.coords = location['coordinates'][0]
        ground.gxlatlonquad.coords = [
            (lowerleft[1], lowerleft[0]),
            (lowerright[1], lowerright[0]),
            (upperright[1], upperright[0]),
            (upperleft[1], upperleft[0])
        ]

        # add timespan
        ground.timespan.begin = res['starttime']
        ground.timespan.end = res['endtime']

        if browse_url:
            ground.icon.href = '%s/browse_small.png' % browse_url
        
    return Response(kml.kml(), headers={'Content-Type': 'application/vnd.google-earth.kml+xml',
                                        'Content-Disposition': 'attachment; filename=%s.kml' % dataset})
    #return jsonify({'results': results})
