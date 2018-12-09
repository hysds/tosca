import traceback
import json
from flask import redirect, abort, request
import requests
import cgi
import base64

from tosca import app


def urs_user_verified(code):
    """Verify user via URS."""

    # urs auth url
    urs_url = "{}/oauth/token".format(app.config['URS_URL'])

    # set authorization value 
    auth_val = base64.b64encode("{}:{}".format(app.config['URS_APP_ID'],
                                               app.config['URS_APP_PASSWORD']))

    # set token exchange payload
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": app.config['URS_REDIRECT_URL'],
    }

    # exchange
    r = requests.post(urs_url, data=payload, headers={ "Authorization": "Basic {}".format(auth_val) })
    try: r.raise_for_status()
    except Exception, e:
        app.logger.error("Got error trying to verify URS user.")
        app.logger.error("%s:\n\n%s" % (str(e), traceback.format_exc()))
        return None
    packet = r.json()
    #app.logger.info("packet: {}".format(json.dumps(packet, indent=2, sort_keys=True)))

    # get user profile
    user_url = "{}{}".format(app.config['URS_URL'], packet['endpoint'])
    #app.logger.info("user_url: {}".format(user_url))
    r = requests.get(user_url, headers={ "Authorization": "{} {}".format(packet['token_type'],
                                                                         packet['access_token']) })
    r.raise_for_status()
    user_info = r.json()
    #app.logger.info("user_info: {}".format(json.dumps(user_info, indent=2, sort_keys=True)))

    # set common fields
    user_info['mail'] = user_info['email_address']

    return user_info
