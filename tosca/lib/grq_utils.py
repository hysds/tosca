from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
import json
import os
from tosca import app

import hysds_commons.request_utils


def mozart_call(method, data={}):
    '''
    Call mozart method with data
    @param method - method to call
    @param data - data to supply to call
    '''
    url = os.path.join(app.config['GRQ_URL'], "api/v0.1", method)
    getpost = "GET"
    res = hysds.lib.request_utils.requests_json_response(
        getpost, url, data=data, verify=False, logger=app.logger)
    return res["result"]


def get_hysds_io_list():
    '''
    Queries GRQ to get HySDS IOs
    '''
    return mozart_call("hysds_io/list")


def get_hysds_io(ident):
    '''
    Queries GRQ to get HySDS Metadata object
    @param ident - identity to get
    '''
    return mozart_call("hysds_io/type", {"id": ident})
