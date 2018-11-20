#!/usr/bin/env python
from tosca import app
from tosca.services.user_rules import create_user_rules_index


create_user_rules_index(app.config['ES_URL'], app.config['USER_RULES_INDEX'])
