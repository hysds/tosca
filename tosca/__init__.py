from tosca.services.dataset import mod as datasetModule
from tosca.services.kml import mod as kmlModule
from tosca.services.user_rules import mod as userRulesModule
from tosca.services.user_tags import mod as userTagsModule
from tosca.services.download import mod as downloadModule
from tosca.services.wget import mod as wgetModule
from tosca.services.query import mod as queryModule
from tosca.views.js import mod as jsModule
from tosca.views.main import mod as viewsModule
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_debugtoolbar import DebugToolbarExtension


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
        location /myprefix {
            proxy_pass http://127.0.0.1:8879;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Scheme $scheme;
            proxy_set_header X-Script-Name /myprefix;
        }

    In apache:
        RewriteEngine on
        RewriteRule "^/search$" "/search/" [R]
        SSLProxyEngine on
        ProxyRequests Off
        ProxyPreserveHost Off
        ProxyPass /search/static !
        ProxyPass /search/ http://localhost:8879/
        ProxyPassReverse /search/ http://localhost:8879/
        <Location /search>
            Header add "X-Script-Name" "/search"
            RequestHeader set "X-Script-Name" "/search"
            Header add "X-Scheme" "https"
            RequestHeader set "X-Scheme" "https"
        </Location>
        Alias /search/static/ /home/ops/sciflo/ops/tosca/tosca/static/
        <Directory /home/ops/sciflo/ops/tosca/tosca/static>
            Options Indexes FollowSymLinks
            AllowOverride All
            Require all granted
        </Directory>

    :param app: the WSGI application
    '''

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        x_forwarded_host = environ.get('HTTP_X_FORWARDED_HOST', '')
        if x_forwarded_host:
            environ['HTTP_HOST'] = x_forwarded_host
        return self.app(environ, start_response)


app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app)
app.config.from_pyfile('../settings.cfg')

# set database config
dbdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(dbdir, 'app.db')
db = SQLAlchemy(app)

# debug toolbar
debug_toolbar = DebugToolbarExtension(app)

# set user auth config
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'views/main.login'

# views blueprints
app.register_blueprint(viewsModule)
app.register_blueprint(jsModule)

# services blueprints
app.register_blueprint(queryModule)
app.register_blueprint(wgetModule)
app.register_blueprint(downloadModule)
app.register_blueprint(userTagsModule)
app.register_blueprint(userRulesModule)
app.register_blueprint(kmlModule)
app.register_blueprint(datasetModule)

# Sub-apps
try:
    from my_jobs.views.my_jobs import VIEW_BLUE as myjobsView
    app.register_blueprint(myjobsView)
    from my_jobs.services.my_jobs import SERV_BLUE as myjobsService
    app.register_blueprint(myjobsService)
    from my_downloads.my_downloads import BLUE as myDownloads
    app.register_blueprint(myDownloads)
except:
    pass
