#!/usr/bin/env python
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()

from requests.exceptions import HTTPError
from tosca.services.user_rules import create_user_rules_index


try:
    create_user_rules_index()
except (HTTPError, Exception) as e:
    if e.response.status_code == 400:
        pass
    else:
        raise e
