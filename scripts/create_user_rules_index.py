#!/usr/bin/env python
from requests.exceptions import HTTPError

from tosca import app
from tosca.services.user_rules import create_user_rules_index

try:
    create_user_rules_index(app.config['ES_URL'], app.config['USER_RULES_INDEX'])
except HTTPError as e:
    if e.response.status_code == 400: pass
    else: raise
