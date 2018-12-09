from datetime import datetime
import hashlib, simpleldap
from flask import (render_template, Blueprint, g, redirect, session, request,
url_for, flash, abort, make_response)
from flask_login import login_required, login_user, logout_user, current_user

from tosca import app, db, lm
from tosca.models.user import User
from tosca.lib.forms import LoginForm
from tosca.lib.ldap import ldap_user_verified
from tosca.lib.urs import urs_user_verified


mod = Blueprint('views/main', __name__)


@lm.user_loader
def load_user(username):
    return User.query.get(username)


@app.before_request
def before_request():
    g.user = current_user


@app.errorhandler(404)
def page_not_found(e):
    error_msg = """Error code 404: Page doesn't exist. Please check the URL. 
                   If you feel there is an issue with our application, 
                   please contact geraldjohn.m.manipon__at__jpl.nasa.gov."""
    return render_template('error.html',
                           title='TOSCA: Encountered Error',
                           current_year=datetime.now().year,
                           error_msg=error_msg), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html',
                           title='TOSCA: Encountered Error',
                           current_year=datetime.now().year,
                           error_msg="Error code 500: " + str(e)), 500


@app.errorhandler(501)
def unimplemented(e):
    return render_template('error.html',
                           title='TOSCA: Encountered Error',
                           current_year=datetime.now().year,
                           error_msg="Error code 501: " + str(e)), 501


@mod.route('/sitemap.xml')
def sitemap():
    #pages = []
    #for rule in app.url_map.iter_rules():
    #    if "GET" in rule.methods and len(rule.arguments) == 0:
    #        pages.append([rule.rule, datetime.utcnow()])
    dt = datetime.utcnow()
    pages = [ [ url_for('views/main.index', _external=True), dt ],
              [ url_for('views/main.login', _external=True), dt ],
              [ url_for('views/main.logout', _external=True), dt] ]
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    resp = make_response(sitemap_xml)
    resp.headers['Content-Type'] = "application/xml"
    return resp


@mod.route('/robots.txt')
def robots():
    txt = render_template('robots.txt')
    resp = make_response(txt)
    resp.headers['Content-Type'] = "text/plain"
    return resp


@mod.route('/login', methods=['GET', 'POST'])
def login():
    #app.logger.info("login args: {}".format(request.args))
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('views/main.index'))

    # authenticate using URS
    if app.config.get('URS_ENABLED', False):
        code = request.args.get('code', None)
        if code is None:
            auth_url = "{}/oauth/authorize?client_id={}&response_type=code&redirect_uri={}"
            return redirect(auth_url.format(app.config['URS_URL'],
                                            app.config['URS_APP_ID'],
                                            app.config['URS_REDIRECT_URL']))
        info = urs_user_verified(code)
        if info is not None:
            username = info['uid']
            user = load_user(username)
            #app.logger.info('user loaded: %s' % user)
            if user is None:
                user = User()
                user.id = username
                user.info = info
                db.session.add(user)
                db.session.commit()
            #app.logger.info('user: %s' % user)
            login_user(user)
            flash("Successfully authenticated.")
            if 'TERMS_OF_USE' in app.config: flash(app.config['TERMS_OF_USE'], 'toc')
            return redirect(request.args.get('next') or url_for('views/main.index'))
        raise RuntimeError("Error trying to authenticate.")

    # authenticate using LDAP and local db
    form = LoginForm()
    if form.validate_on_submit():
        #session['remember_me'] = form.remember_me.data 
        username = form.username.data
        password = form.password.data
        # authenticate ops user account
        if username == app.config['OPS_USER']:
            ops_passwd_hex = hashlib.sha224(password).hexdigest()
            if app.config['OPS_PASSWORD_HASH'] == ops_passwd_hex:
                info = {}
            else: info = None 
        elif username in app.config.get('OUTSIDE_ACCOUNTS', {}):
            passwd_hex = hashlib.sha224(password).hexdigest()
            if app.config['OUTSIDE_ACCOUNTS'][username] == passwd_hex:
                info = {}
            else: info = None
        else:
            # for everyone else authenticate via LDAP
            info = ldap_user_verified(username, password)
        if info is not None:
            user = load_user(username)
            #app.logger.info('user loaded: %s' % user)
            if user is None:
                user = User()
                user.id = form.username.data
                user.info = info
                db.session.add(user)
                db.session.commit()
            #app.logger.info('user: %s' % user)
            login_user(user)
            flash("Successfully authenticated.")
            if 'TERMS_OF_USE' in app.config: flash(app.config['TERMS_OF_USE'], 'toc')
            return redirect(request.args.get('next') or url_for('views/main.index'))
        flash("Error trying to authenticate.")
    else:
        for error in form.errors:
            flash('%s: %s' % (error, '; '.join(form.errors[error])))
    return render_template('login_jpl.html',
                           title='TOSCA: Advanced FacetView User Interface',
                           form=form, current_year=datetime.now().year)


@mod.route('/logout')
def logout():
    logout_user()
    if app.config.get('URS_ENABLED', False):
        auth_url = "{}/logout?redirect_uri={}"
        return redirect(auth_url.format(app.config['URS_URL'],
                                        app.config['URS_REDIRECT_URL']))
    flash("Successfully logged out.")
    return redirect(url_for('views/main.index'))


@mod.route('/')
@login_required
def index():
    #app.logger.debug("Got here: index")
    #app.logger.debug("g.user: %s" % g.user)
    #app.logger.debug("g.user.info: %s" % g.user.info)
    emails = g.user.info.get('mail', [])
    if len(emails) > 0: email = emails[0]
    else: email = ""
    g.blueprints = app.blueprints
    return render_template('facetview.html',
                           title='TOSCA: Advanced FacetView User Interface',
                           email= email,
                           current_year=datetime.now().year)


@mod.route('/download/<dataset>', methods=['GET'])
@login_required
def download(dataset=None):
    source = request.args.get('source')
    if dataset is None:
        abort(500, "No dataset specified.")
    return render_template('download.html',
                           title='TOSCA: Advanced FacetView User Interface',
                           dataset=dataset, source=source,
                           current_year=datetime.now().year)


@mod.route('/mapview')
@login_required
def mapview():
    #app.logger.debug("Got here: index")
    #app.logger.debug("g.user: %s" % g.user)
    #app.logger.debug("g.user.info: %s" % g.user.info)
    emails = g.user.info.get('mail', [])
    if len(emails) > 0: email = emails[0]
    else: email = ""
    return render_template('facetview_gibs.html',
                           title='TOSCA: Advanced FacetView User Interface',
                           email= email,
                           current_year=datetime.now().year)


@mod.route('/jpl')
def jpl():
    #app.logger.debug("Got here: index")
    #app.logger.debug("g.user: %s" % g.user)
    #app.logger.debug("g.user.info: %s" % g.user.info)
    return render_template('jpl.html',
                           title='TOSCA: Advanced FacetView User Interface',
                           current_year=datetime.now().year)


@mod.route('/jpl_login', methods=['GET', 'POST'])
def jpl_login():
    form = LoginForm()
    if form.validate_on_submit():
        #session['remember_me'] = form.remember_me.data 
        username = form.username.data
        password = form.password.data
    else:
        for error in form.errors:
            flash('%s: %s' % (error, '; '.join(form.errors[error])))
    return render_template('login_jpl.html',
                           title='TOSCA: Advanced FacetView User Interface',
                           form=form, current_year=datetime.now().year)


