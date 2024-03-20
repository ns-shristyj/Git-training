# Imports
import os
import uuid
import re
import json
import logging
import requests
import platform
from datetime import timedelta
from jsonpath_ng import jsonpath, parse
from dotenv import load_dotenv, dotenv_values, set_key

from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.writer.write_anything import write_file
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document
from spdx_tools.spdx.model.document import Document
from spdx_tools.spdx.parser.error import SPDXParsingError

from flask import Flask, render_template, url_for, request, make_response, redirect, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy import update
from flask_jwt_extended import JWTManager, create_access_token, set_access_cookies, jwt_required, get_jwt_identity, unset_jwt_cookies
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler

from models import db, User, Vendor, Component, Vulnerability

from authlib.integrations.flask_client import OAuth

load_dotenv('.env')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
app.config['JWT_COOKIE_SECURE'] = True  # Set to False if not using https
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # CSRF protection
app.config['PLATFORM'] = platform.system()

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['DATA_PATH'] = os.path.join(basedir, 'data')
app.config['TEMP_PATH'] = os.path.join(basedir, 'temp')
app.config['ALLOWED_EXT'] = ["json", "xml", "spdx", "xlsx", "csv"]
app.config['CYDX_MAC_PATH'] = os.path.join(basedir, 'cyclonedx-osx-x64')
app.config['CYDX_WIN_PATH'] = os.path.join(basedir, 'cyclonedx-win-x64.exe')
app.config['CYDX_LIN_PATH'] = os.path.join(basedir, 'cyclonedx-linux-x64')
app.config['DB_PATH'] = os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


oauth = OAuth(app)

auth0 = oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


# Remove the basic configuration for the root logger
logging.basicConfig(level=logging.NOTSET)

# Configure logging for the application
app_log = logging.getLogger('app')
app_log.setLevel(logging.INFO)
app_handler = logging.FileHandler('logs/app.log')
app_handler.setLevel(logging.INFO)
app_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
app_handler.setFormatter(app_formatter)
app_log.addHandler(app_handler)

# Configure logging for Werkzeug (HTTP logs)
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.DEBUG)
werkzeug_handler = logging.FileHandler('logs/http.log')
werkzeug_handler.setLevel(logging.INFO)
werkzeug_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
werkzeug_handler.setFormatter(werkzeug_formatter)
werkzeug_log.addHandler(werkzeug_handler)

#app_log.debug('This is a debug message')
#app_log.info('This is an info message')
#app_log.warning('This is a warning message')
#app_log.error('This is an error message')
#app_log.critical('This is a critical message')


db.init_app(app)
jwt = JWTManager(app)

# Function to check if a route requires being logged in and confirmed
def requires_confirmed_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if JWT or session indicates user is logged in
        # This example uses JWT. Adapt according to your auth method.
        current_user_id = get_jwt_identity()
        if current_user_id:
            user = User.query.filter_by(public_id=current_user_id).first()
            if user and not user.confirmed:
                # User is not confirmed. Redirect to login.
                flash("Your account has not been confirmed. Please wait until your account is confirmed by an Admin.", "error")
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to check if a route requires being logged in
def requires_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if JWT or session indicates user is logged in
        # This example uses JWT. Adapt according to your auth method.
        current_user_id = get_jwt_identity()
        if current_user_id:
            user = User.query.filter_by(public_id=current_user_id).first()
            if user and (user.role != "Admin" and user.role != "Super Admin"):
                flash("Unauthorized.", "error")
                return redirect(request.referrer or url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def block_read_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if JWT or session indicates user is logged in
        # This example uses JWT. Adapt according to your auth method.
        current_user_id = get_jwt_identity()
        if current_user_id:
            user = User.query.filter_by(public_id=current_user_id).first()
            if user and user.role == "User":
                flash("Unauthorized.", "error")
                return redirect(request.referrer or url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------
#   Record Management
# ---------------------
#
# Record management, including vendors, components, vulnerabilities, etc.

# -- Templates --

@app.route('/')
@app.route('/index')
@jwt_required()
@requires_confirmed_user
def index():
    user_public_id = get_jwt_identity()

    user = User.query.filter_by(public_id=user_public_id).first()
    
    vendors = Vendor.query.order_by(Vendor.created_date.desc()).limit(6).all()
    return render_template('index.html', vendors=vendors, user=user)

@app.route('/vendor/<int:vendor_id>')
@jwt_required()
@requires_confirmed_user
@block_read_only
def vendor(vendor_id):
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    vendor = Vendor.query.get_or_404(vendor_id)

    vulnerabilities = Vulnerability.query.join(Component).filter(Component.vendor_id == vendor_id).all()

    components = Component.query.filter_by(vendor_id=vendor_id).all()
        
    return render_template('vendor.html', vendor=vendor, user=user, components=components, vulnerabilities=vulnerabilities)

@app.route('/component/<int:component_id>')
@jwt_required()
@requires_confirmed_user
@block_read_only
def component(component_id):
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    component = Component.query.get_or_404(component_id)
    vendor = Vendor.query.filter_by(id=component.vendor_id).first()
        
    return render_template('component.html', component=component, user=user, vendor=vendor)

@app.route('/vulnerability/<int:vulnerability_id>')
@jwt_required()
@requires_confirmed_user
@block_read_only
def vulnerability(vulnerability_id):
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    vulnerability = Vulnerability.query.get_or_404(vulnerability_id)
    components = Component.query.filter_by(id=vulnerability.component_id).all()
    vendor = Vendor.query.filter_by(id=components[0].vendor_id).first()
        
    return render_template('vulnerability.html', vulnerability=vulnerability, components=components, user=user, vendor=vendor)

@app.route('/components')
@jwt_required()
@requires_confirmed_user
@block_read_only
def components():
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    components = Component.query.all()

    for component in components:
        vendor = Vendor.query.filter_by(id=component.vendor_id).first()
        component.vendor = vendor
        
    return render_template('components.html', user=user, components=components)

@app.route('/vulnerabilities')
@jwt_required()
@requires_confirmed_user
@block_read_only
def vulnerabilities():
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    vulnerabilities = Vulnerability.query.all()

    for vulnerability in vulnerabilities:
        component = Component.query.filter_by(id=vulnerability.component_id).first()
        vendor = Vendor.query.filter_by(id=component.vendor_id).first()
        vulnerability.component = component
        vulnerability.vendor = vendor
        
    return render_template('vulnerabilities.html', user=user, vulnerabilities=vulnerabilities)


@app.route('/vendors')
@jwt_required()
@requires_confirmed_user
@block_read_only
def vendors():
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    vendors = Vendor.query.all()

    for vendor in vendors:
        # Initialize severity counts
        vendor.low_severity = 0
        vendor.medium_severity = 0
        vendor.high_severity = 0
        vendor.critical_severity = 0

        # Iterate through each component of the vendor
        for component in vendor.components:
            # Iterate through each vulnerability of the component
            for vulnerability in component.vulnerabilities:
                # Increment the appropriate severity count
                if vulnerability.severity == 'Low':
                    vendor.low_severity += 1
                elif vulnerability.severity == 'Medium':
                    vendor.medium_severity += 1
                elif vulnerability.severity == 'High':
                    vendor.high_severity += 1
                elif vulnerability.severity == 'Critical':
                    vendor.critical_severity += 1
                    

    return render_template('vendors.html', user=user, vendors=vendors)

# -- API --

@app.route('/api/internal/vendor/<int:vendor_id>', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def update_vendor(vendor_id):
    try:
        vendor = Vendor.query.filter_by(id=vendor_id).first()
        vendor_name = vendor.name
        if vendor.id == vendor_id:
            try:
                if request.content_type == "application/x-www-form-urlencoded":
                    body = request.form
                    print(body)
                    new_name = body['name']
                    if new_name == "" or re.search(r"[\<\\\/\>]+", new_name):
                        raise Exception(f"Invalid vendor name.")
                    try:
                        new_status = body['active']
                        if new_status == "on":
                            new_status = True
                        else:
                            raise Exception('Invalid active value, leave null to disable vendor.')
                    except KeyError:
                        new_status = None
                elif request.content_type == "application/json":
                    body = request.json
                    print(body)
                    new_name = body['name']
                    new_status = body['active']
                    if new_name == "" or re.search(r"[\<\\\/\>]+", new_name):
                        raise Exception(f"Invalid vendor name.")
                    try:
                        new_status = body['active']
                        if new_status == "on":
                            new_status = True
                        else:
                            raise Exception('Invalid active value, leave null to disable vendor.')
                    except KeyError:
                        new_status = None
                else:
                    raise Exception(f"Invalid content type.")
                try:
                    changes = {"previous_name": f"{body['name']}", "previous_active": f"{body['active']}", "new_name": f"{new_name}", "new_active": f"{new_status}"}
                except KeyError:
                    try:
                        changes = {"previous_name": f"{body['name']}", "previous_active": f"{body['active']}", "new_name": f"{new_name}"}
                    except KeyError:
                        changes = {"previous_name": f"{body['name']}", "new_name": f"{new_name}"}
                print(new_name)
                print(new_status)
                db.session.execute((update(Vendor).where(Vendor.id.in_([vendor_id])).values(name=str(new_name), active=bool(new_status))))
                db.session.commit()
                vendor_name = str(new_name)
            except Exception as e:
                raise Exception(f"DB Failed to update vendor with the following id: {vendor_id}, reason: {e}")
            app_log.info({"status": "Success", "message": f"Vendor with the following name:id was updated: {vendor_name}:{vendor_id}, changes: {changes}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"{vendor_name} was updated.", "info")
                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
            else:
                return(jsonify({"status":200, "message": f"Vendor with the following name:id was updated: {vendor_name}:{vendor_id}"}))
        else:
            raise Exception(f"Failed to update vendor with the following id: {vendor_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Vendor was not found or failed to be updated, check app.log for more information.", "error")
            return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))
        


@app.route('/api/internal/vendor/add', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def add_vendor():
    try:
        current_user = User.query.filter_by(public_id=get_jwt_identity()).first()
        print(current_user)
        if request.content_type == "application/x-www-form-urlencoded":
            body = request.form
            print(body)
            name = body['name']
            if name == "" or re.search(r"[\<\\\/\>]+", name):
                raise Exception(f"Invalid vendor name.")
            try:
                status = body['checked']
                if status == "on":
                    status = True
                else:
                    raise Exception('Invalid active value, leave null to disable vendor.')
            except KeyError:
                status = None
        elif request.content_type == "application/json":
            body = request.json
            print(body)
            name = body['name']
            if name == "" or re.search(r"[\<\\\/\>]+", name):
                raise Exception(f"Invalid vendor name.")
            try:
                status = body['checked']
                if status == "on":
                    status = True
                else:
                    raise Exception('Invalid active value, leave out of request to disable vendor. (Just send name)')
            except KeyError:
                status = None
        else:
            raise Exception(f"Invalid content type.")
        print(name)
        print(status)
        if status == None:
            new_vendor = Vendor(name=name, created_by=current_user, active=False)
            db.session.add(new_vendor)
            db.session.commit()
            vendor_name = str(name)
        else:
            new_vendor = Vendor(name=name, created_by=current_user, active=True)
            db.session.add(new_vendor)
            db.session.commit()
            vendor_name = str(name)
        app_log.info({"status": "Success", "message": f"Vendor with the following name:id was created: {vendor_name}:{new_vendor.id}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash(f"{vendor_name} was created.", "info")
            return make_response(redirect(url_for('vendors')))
        else:
            return(jsonify({"status":200, "message": f"Vendor with the following name:id was created: {vendor_name}:{new_vendor.id}"}))
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Vendor could not be created, check app.log for more information.", "error")
            return make_response(redirect(url_for('vendors')))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))


@app.route('/api/internal/vendor/<int:vendor_id>/delete', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def delete_vendor(vendor_id):
    try:
        vendor = Vendor.query.filter_by(id=vendor_id).first()
        vendor_name = vendor.name
        if vendor.id == vendor_id:
            db.session.delete(vendor)
            db.session.commit()
            app_log.info({"status": "Success", "message": f"Vendor with the following name:id was deleted: {vendor_name}:{vendor_id}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"{vendor_name} was deleted.", "info")
                return make_response(redirect(url_for('vendors')))
            else:
                return(jsonify({"status":200, "message": f"Vendor with the following name:id was deleted: {vendor_name}:{vendor_id}"}))
        else:
            raise Exception(f"Failed to delete vendor with the following id: {vendor_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Vendor was not found or failed to be deleted, check app.log for more information.", "error")
            return make_response(redirect(url_for('vendors')))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))
        

@app.route('/api/internal/vendor/<int:vendor_id>/data/delete', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def delete_vendor_data(vendor_id):
    try:
        vendor = Vendor.query.filter_by(id=vendor_id).first()
        vendor_name = vendor.name
        if vendor.id == vendor_id:
            for i in vendor.components:
                try:
                    component = Component.query.filter_by(id=i.id).first()
                    db.session.delete(component)
                except Exception as e:
                        db.session.rollback()
                        raise Exception(f"Failed to delete all data for vendor with the following id: {vendor_id}")
            else:
                db.session.commit()
            app_log.info({"status": "Success", "message": f"All data deleted for vendor with the following name:id : {vendor_name}:{vendor_id}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"All data for {vendor_name} was deleted.", "info")
                return make_response(redirect(url_for('vendors')))
            else:
                return(jsonify({"status":200, "info": f"All data deleted for vendor with the following name:id: {vendor_name}:{vendor_id}"}))
        else:
            raise Exception(f"Failed to delete all data for vendor with the following id: {vendor_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Vendor was not found or deletion was unsuccessful, check app.log for more information.", "error")
            return make_response(redirect(url_for('vendors')))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))


@app.route('/api/internal/component/<int:component_id>', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def update_component(component_id): 
    try:
        component = Component.query.filter_by(id=component_id).first()
        component_name = component.name
        
        if component.id == component_id:
            try:
                if request.content_type == "application/x-www-form-urlencoded":
                    body = request.form
                    print(body)
                    new_name = body.get("name", default="N/A")
                    new_desc = body.get("description", default="N/A")
                    new_ver = body.get("version", default="N/A")
                    new_vcs = body.get("vcs", default="N/A")
                    new_lic = body.get("license", default="N/A")
                    new_purl = body.get("package_url", default="N/A")
                    new_hash = body.get("hash", default="N/A")
                    new_haty = body.get("hash_type", default="N/A")
                            
                elif request.content_type == "application/json":
                    body = request.json
                    print(body)
                    new_name = body.get("name", default="N/A")
                    new_desc = body.get("description", default="N/A")
                    new_ver = body.get("version", default="N/A")
                    new_vcs = body.get("vcs", default="N/A")
                    new_lic = body.get("license", default="N/A")
                    new_purl = body.get("package_url", default="N/A")
                    new_hash = body.get("hash", default="N/A")
                    new_haty = body.get("hash_type", default="N/A")
                    
                else:
                    raise Exception(f"Invalid content type.")
                changes = {"prev_name": f"{component.name}", "prev_desc": f"{component.description}", "prev_ver": f"{component.version}", "prev_vcs": f"{component.vcs}", "prev_lic": f"{component.license}", "prev_purl": f"{component.package_url}","prev_hash": f"{component.hash}", "prev_haty": f"{component.hash_type}",
                           "new_name": f"{body.get("name", default="N/A")}", "new_desc": f"{body.get("description", default="N/A")}", "new_ver": f"{body.get("version", default="N/A")}", "new_vcs": f"{body.get("vcs", default="N/A")}", "new_lic": f"{body.get("license", default="N/A")}", "new_purl": f"{body.get("package_url", default="N/A")}","new_hash": f"{body.get("hash", default="N/A")}", "new_haty": f"{body.get("hash_type", default="N/A")}"}
                db.session.execute((update(Component).where(Component.id.in_([component_id])).values(name=str(new_name), description=str(new_desc), version=str(new_ver), vcs=str(new_vcs), license=str(new_lic), package_url=str(new_purl), hash=str(new_hash), hash_type=str(new_haty))))
                db.session.commit()
                component_name = str(new_name)
            except Exception as e:
                raise Exception(f"DB Failed to update component with the following id: {component_id}, reason: {e}")
            app_log.info({"status": "Success", "message": f"Component with the following name:id was updated: {component_name}:{component_id}, changes: {changes}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"{component_name} was updated.", "info")
                return make_response(redirect(url_for('component', component_id=component_id)))
            else:
                return(jsonify({"status":200, "message": f"Component with the following name:id was updated: {component_name}:{component_id}"}))
        else:
            raise Exception(f"Failed to update component with the following id: {component_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Component was not found or failed to be updated, check app.log for more information.", "error")
            return make_response(redirect(url_for('component', component_id=component_id)))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))


@app.route('/api/internal/component/<int:component_id>/delete', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def delete_component(component_id):
    try:
        component = Component.query.filter_by(id=component_id).first()
        vendor_id = component.vendor_id
        component_name = component.name
        if component.id == component_id:
            db.session.delete(component)
            db.session.commit()
            app_log.info({"status": "Success", "message": f"Component with the following name:id was deleted: {component_name}:{component_id}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"{component_name} was deleted.", "info")
                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
            else:
                return(jsonify({"status":200, "message": f"Component with the following name:id was deleted: {component_name}:{component_id}"}))
        else:
            raise Exception(f"Failed to delete component with the following id: {component_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Component was not found or failed to be deleted, check app.log for more information.", "error")
            return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))


@app.route('/api/internal/vulnerability/<int:vulnerability_id>', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def update_vulnerability(vulnerability_id):
    try:
        vulnerability = Vulnerability.query.filter_by(id=vulnerability_id).first()
        vulnerability_name = vulnerability.name
        
        if vulnerability.id == vulnerability_id:
            try:
                if request.content_type == "application/x-www-form-urlencoded":
                    body = request.form
                    print(body)
                    new_name = body.get("name", default="N/A")
                    new_sev = body.get("severity", default="N/A")
                    new_cwe = body.get("cwe", default="N/A")
                    new_cvs = body.get("cvss_score", default="N/A")
                    new_cvt = body.get("cvss_type", default="N/A")
                            
                elif request.content_type == "application/json":
                    body = request.json
                    print(body)
                    new_name = body.get("name", default="N/A")
                    new_sev = body.get("severity", default="N/A")
                    new_cwe = body.get("cwe", default="N/A")
                    new_cvs = body.get("cvss_score", default="N/A")
                    new_cvt = body.get("cvss_type", default="N/A")
                    
                else:
                    raise Exception(f"Invalid content type.")
                changes = {"prev_name": f"{vulnerability.name}", "prev_sev": f"{vulnerability.severity}", "prev_cwe": f"{vulnerability.cwe}", "prev_cvs": f"{vulnerability.cvss_score}", "prev_cvt": f"{vulnerability.cvss_type}",
                           "new_name": f"{body.get("name", default="N/A")}", "new_sev": f"{body.get("severity", default="N/A")}", "new_cwe": f"{body.get("cwe", default="N/A")}", "new_cvs": f"{body.get("cvs", default="N/A")}", "new_cvt": f"{body.get("cvss_type", default="N/A")}"}
                db.session.execute((update(Vulnerability).where(Vulnerability.id.in_([vulnerability_id])).values(name=str(new_name), severity=str(new_sev), cwe=str(new_cwe), cvss_score=str(new_cvs), cvss_type=str(new_cvt))))
                db.session.commit()
                vulnerability_name = str(new_name)
            except Exception as e:
                raise Exception(f"DB Failed to update vulnerability with the following id: {vulnerability_id}, reason: {e}")
            app_log.info({"status": "Success", "message": f"Vulnerability with the following name:id was updated: {vulnerability_name}:{vulnerability_id}, changes: {changes}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"{vulnerability_name} was updated.", "info")
                return make_response(redirect(url_for('vulnerability', vulnerability_id=vulnerability_id)))
            else:
                return(jsonify({"status":200, "message": f"Vulnerability with the following name:id was updated: {vulnerability_name}:{vulnerability_id}"}))
        else:
            raise Exception(f"Failed to update vulnerability with the following id: {vulnerability_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Vulnerability was not found or failed to be updated, check app.log for more information.", "error")
            return make_response(redirect(url_for('vulnerability', vulnerability_id=vulnerability_id)))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))


@app.route('/api/internal/vulnerability/<int:vulnerability_id>/delete', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def delete_vulnerability(vulnerability_id):
    try:
        vulnerability = Vulnerability.query.filter_by(id=vulnerability_id).first()
        component_id = vulnerability.component_id
        component = Component.query.filter_by(id=component_id).first()
        vendor_id = component.vendor_id
        vulnerability_name = vulnerability.name
        if vulnerability.id == vulnerability_id:
            db.session.delete(vulnerability)
            db.session.commit()
            app_log.info({"status": "Success", "message": f"Vulnerability with the following name:id was deleted: {vulnerability_name}:{vulnerability_id}"})
            if request.content_type == "application/x-www-form-urlencoded":
                flash(f"{vulnerability_name} was deleted.", "info")
                return make_response(redirect(url_for(f'vendor', vendor_id=vendor_id)))
            else:
                return(jsonify({"status":200, "message": f"Vulnerability with the following name:id was deleted: {vulnerability_name}:{vulnerability_id}"}))
        else:
            raise Exception(f"Failed to delete vulnerability with the following id: {vulnerability_id}")
    except Exception as e:
        app_log.error({"status": "Error", "message": f"{e}"})
        if request.content_type == "application/x-www-form-urlencoded":
            flash("Vulnerability was not found or failed to be deleted, check app.log for more information.", "error")
            return make_response(redirect(url_for(f'vendor', vendor_id=vendor_id)))
        else:
            return(jsonify({"status":404, "error": f"{e}"}))


@app.route('/api/internal/sbom/upload', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def upload_sbom():
    def fetchConfig():
        check = {}
        try:
            config = app.config
            check['status'] = "Success"
            check['message'] = "Config loaded successfully..."
            check['config'] = config
            return (check)
        except Exception as e:
            check['status'] = "Error"
            check['message'] = f"{e}"
            return (check)
    
    def store_in_localdb(data, type):
        
        def schema_check(pack=None, comp=None):
            if pack:
                schema = {"name":str,"description":str,"version":str,"vcs":str,"license":str,"package_url":str,"hash":str,"hash_type":str}
                try:
                    schema['name'] = pack['name']
                except KeyError:
                    schema['name'] = "N/A"
                try:
                    schema['description'] = pack['description']
                except KeyError:
                    try:
                        schema['description'] = pack['summary']
                    except KeyError:
                        schema['description'] = "N/A"
                try:
                    schema['version'] = pack['versionInfo']
                except KeyError:
                    schema['version'] = "N/A"
                try:
                    for refs in pack['externalRef']:
                        if refs['referenceCategory'] == "packageManager":
                            schema['vcs'] = refs['referenceLocator']
                except KeyError:
                    schema['vcs'] = "N/A"
                try:
                    schema['license'] = pack['licenseDeclared']
                except KeyError:
                    schema['license'] = "N/A"
                try:
                    if pack['downloadLocation'] != "NOASSERTION":
                        schema['package_url'] = pack['downloadLocation']
                    elif pack['sourceInfo'] != "NOASSERTION":
                        schema['package_url'] = pack['sourceInfo']
                    else:
                        schema['package_url'] = "N/A"
                except KeyError:
                    schema['package_url'] = "N/A"
                try:
                    for checksums in pack['checksums']:
                        if checksums['algorithm'] == "SHA256":
                            schema['hash'] = checksums['checksumValue']
                            schema['hash_type'] = checksums['algorithm']
                        else:
                            continue
                    for checksums in pack['checksums']:
                        if checksums['algorithm'] == ("SHA1" or "SHA512" or "MD5"):
                            schema['hash'] = checksums['checksumValue']
                            schema['hash_type'] = checksums['algorithm']
                        else:
                            continue
                except KeyError:
                    try:
                        schema['hash'] = pack['packageVerificationCode']['packageVerificationCodeValue']
                        schema['hash_type'] = "SHA1"
                    except KeyError:
                        schema['hash'] = "N/A"
                        schema['hash_type'] = "N/A"
                for key in schema.keys():
                    if schema[key] == "NOASSERTION":
                        schema[key] = "N/A"
                return(schema)
            elif comp:
                schema = {"name":str,"description":str,"version":str,"vcs":str,"license":str,"package_url":str,"hash":str,"hash_type":str}
                try:
                    schema['name'] = comp['name']
                except KeyError:
                    schema['name'] = "N/A"
                try:
                    schema['description'] = comp['description']
                except KeyError:
                    schema['description'] = "N/A"
                try:
                    schema['version'] = comp['version']
                except KeyError:
                    schema['version'] = "N/A"
                try:
                    for refs in comp['externalReferences']:
                        if refs['type'] == "vcs":
                            schema['vcs'] = refs['url']
                            break
                        else:
                            schema['vcs'] = ""
                    if schema['vcs'] == "":
                        schema['vcs'] = "N/A"
                except KeyError:
                    schema['vcs'] = "N/A"
                try:                    
                    licenses = []
                    for license in comp['licenses']:
                        try:
                            licenses.append(license['license']['id'])
                        except KeyError:
                            continue
                    for license in comp['licenses']:
                        try:
                            licenses.append(license['license']['name'])
                        except KeyError:
                            continue
                    licenses = ", ".join(licenses)
                    schema['license'] = licenses
                except KeyError:
                    schema['license'] = "N/A"
                try:
                    schema['package_url'] = comp['purl']
                except KeyError:
                    schema['package_url'] = "N/A"
                try:
                    for hash in comp['hashes']:
                        if hash['alg'] == "SHA-256":
                            schema['hash'] = hash['content']
                            schema['hash_type'] = "SHA256"
                        else:
                            continue
                    for hash in comp['hashes']:
                        if hash['alg'] == "SHA-1":
                            schema['hash'] = hash['content']
                            schema['hash_type'] = "SHA1"
                        elif hash['alg'] == "SHA-512":
                            schema['hash'] = hash['content']
                            schema['hash_type'] = "SHA512"
                        elif hash['alg'] == "MD5":
                            schema['hash'] = hash['content']
                            schema['hash_type'] = "MD5"
                        else:
                            continue
                except KeyError:
                    schema['hash'] = "N/A"
                    schema['hash_type'] = "N/A"
                return(schema)
        
        check = {}
        if type == "spdx":
            try:
                vendor_id = request.form.get('vendor_id')
                data = json.load(open(data))
                packages = data['packages']
                for pack in packages:
                    try:
                        pack = schema_check(pack=pack)
                        new_pack = Component(name=pack['name'], description=pack['description'], version=pack['version'], vcs=pack['vcs'], license=pack['license'], package_url=pack['package_url'], hash=pack['hash'], hash_type=pack['hash_type'], vendor_id=int(vendor_id))
                        db.session.add(new_pack)
                    except Exception as e:
                        db.session.rollback()
                        check['status'] = "Error"
                        check['message'] = f"{e}"
                        return(check)
                else:
                    db.session.commit()
                check['status'] = "Success"
                check['message'] = 'Upload to database successful'
                return(check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return(check)
        elif type == "cydx":
            try:
                vendor_id = request.form.get('vendor_id')
                data = json.load(open(data))
                components = data['components']
                for comp in components:
                    try:
                        comp = schema_check(comp=comp)
                        new_comp = Component(name=comp['name'], description=comp['description'], version=comp['version'], vcs=comp['vcs'], license=comp['license'], package_url=comp['package_url'], hash=comp['hash'], hash_type=comp['hash_type'], vendor_id=int(vendor_id))
                        db.session.add(new_comp)
                    except Exception as e:
                        db.session.rollback()
                        check['status'] = "Error"
                        check['message'] = f"{e}"
                        return(check)
                else:
                    db.session.commit()
                check['status'] = "Success"
                check['message'] = 'Upload to database successful'
                return(check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return(check)
    
    def convert_to_json(data, temp, cyclone_path=None, spdx=None, cyclone=None):
        check = {}

        try:
            if spdx:
                try:
                    spdxDoc = parse_file(os.path.abspath(data))
                    write_file(document=spdxDoc, file_name=os.path.abspath(temp), validate=True)
                    check['status'] = "Success"
                    check['message'] = "Successfully converted spdx file to json."
                    return (check)
                except Exception as e:
                    check['status'] = "Error"
                    check['message'] = f"{e}"
                    return (check)
            elif cyclone:
                try:
                    response = os.popen(f'"{cyclone_path}" convert --input-file "{os.path.abspath(data)}" --input-format autodetect --output-format json --output-file "{os.path.abspath(temp)}"').read()
                    check['status'] = "Success"
                    check['message'] = "Successfully converted cyclone-dx file to json."
                    return (check)
                except Exception as e:
                    check['status'] = "Error"
                    check['message'] = f"{e}"
                    return (check)
        except Exception as e:
            check['status'] = "Error"
            check['message'] = f"{e}"
            return (check)
    
    def generate_uuid(filename):
        tokenization = {}
        id = str(uuid.uuid1())
        #hash = hashlib.file_digest(file, "SHA256").hexdigest()
        extension = filename.split(".")[-1]
        tokenization['fileId'] = id
        #tokenization['sha256'] = hash
        tokenization['ext'] = extension
        return (tokenization)
    
    def check_extension(filename, allowedExt):
        extension = filename.split(".")[-1]
        if extension in allowedExt:
            return (True)
        else:
            return (False)
    
    def validate_file(fileIn, cyclone_path):
        
        def cyclone_check(doc, cyclone_path):
            check = {}

            try:
                result = os.popen(f'"{cyclone_path}" validate --fail-on-errors --input-file "{doc}" --input-format autodetect').readlines()

                if result == []:
                    check['status'] = "Error"
                    check['message'] = f"Invalid file format"
                    return (check)
                elif result != []:
                    for i in result:
                        if "BOM is not valid." in i or "Unable to auto-detect input format" in i:
                            check['status'] = "Error"
                            check['message'] = f"{result}"
                            return (check)
                    check['status'] = "Success"
                    check['message'] = f"{result}"
                    return (check)
            except os.error as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
        
        def spdx_check(doc):
            check = {}

            try:
                spdxDoc = parse_file(doc)
                validate = validate_full_spdx_document(spdxDoc)
                check['status'] = "Success"
                check['message'] = "SPDX format detected"
                return (check)
            except SPDXParsingError as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
            except AttributeError as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
        
        check = {}

        firstCheck = spdx_check(os.path.abspath(fileIn))
        if firstCheck['status'] == "Success":
            check['status'] = "Success"
            check['message'] = f"File validated with SPDX-Tools"
            check['method'] = "spdx"
            return (check)
        elif firstCheck['status'] == "Error":
            secondCheck = cyclone_check(os.path.abspath(fileIn), os.path.abspath(cyclone_path))
            if secondCheck['status'] == "Success":
                check['status'] = "Success"
                check['message'] = f"File validated with CycloneDX"
                check['method'] = "cydx"
                return (check)
            elif secondCheck['status'] == "Error":
                check['status'] = "Error"
                check['message'] = f"Un-supported file type. Please use a supported file type. File:{os.path.abspath(fileIn)}"
                return (check)


    config_check = fetchConfig()
    vendor_id = request.form.get('vendor_id')
    if config_check['status'] == "Success":
        config = config_check['config']
        print(config)
        tempFolder = f'{os.path.abspath(config['TEMP_PATH'])}'
        print(tempFolder)
        dataFolder = f'{os.path.abspath(config['DATA_PATH'])}'
        print(dataFolder)
        allowedExt = f'{config['ALLOWED_EXT']}'

        if 'sbomFile' not in request.files:
            if request.content_type == "application/x-www-form-urlencoded":
                flash("No file found", "error")
                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
            else:
                return (jsonify({"status": 400, "message": "No file found"}))

        file = request.files['sbomFile']
        if file.filename == '':
            if request.content_type == "application/x-www-form-urlencoded":
                flash("File must have a name", "error")
                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
            else:
                return (jsonify({"status": 400, "message": "File must have a name"}))

        if file and check_extension(file.filename, allowedExt):
            tokenz = generate_uuid(file.filename)
            dataUpload = os.path.join(dataFolder, tokenz['fileId'] + "." + tokenz['ext'])
            file.save(dataUpload)
            
            if config['PLATFORM'] == "Windows":
                check = validate_file(dataUpload, config['CYDX_WIN_PATH'])
                app_log.info(f"{check}")
                if check['status'] == "Success":
                    tempUpload = os.path.join(tempFolder, str(tokenz['fileId']) + ".json")
                    
                    if check['method'] == "spdx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, spdx=True)
                        app_log.info(f"{check}")
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), "spdx")
                            if check['status'] == "Success":
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    flash("Upload successful", "info")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    flash("Upload was unsuccessful, please check app.log for more information", "error")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            if request.content_type == "application/x-www-form-urlencoded":
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                flash("Upload was unsuccessful, please check app.log for more information", "error")
                                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                            else:
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))

                    elif check['method'] == "cydx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, cyclone_path=config['CYDX_WIN_PATH'], cyclone=True)
                        app_log.info(f"{check}")
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), "cydx")
                            if check['status'] == "Success":
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    flash("Upload successful", "info")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    flash("Upload was unsuccessful, please check app.log for more information", "error")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            if request.content_type == "application/x-www-form-urlencoded":
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                flash("Upload was unsuccessful, please check app.log for more information", "error")
                                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                            else:
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                elif check['status'] == "Error":
                    os.remove(dataUpload)
                    if request.content_type == "application/x-www-form-urlencoded":
                        app_log.error({"status": 400, "message": f"{check['message']}"})
                        flash("Upload was unsuccessful, please check app.log for more information", "error")
                        return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                    else:
                        app_log.error({"status": 400, "message": f"{check['message']}"})
                        return (jsonify({"status": 400, "message": f"{check['message']}"}))

            elif config['PLATFORM'] == "Linux":
                check = validate_file(dataUpload, config['CYDX_LIN_PATH'])
                app_log.info(f"{check}")
                if check['status'] == "Success":
                    tempUpload = os.path.join(tempFolder, str(tokenz['fileId']) + ".json")
                    if check['method'] == "spdx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, spdx=True)
                        app_log.info(f"{check}")
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), "spdx")
                            if check['status'] == "Success":
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    flash("Upload successful", "info")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    flash("Upload was unsuccessful, please check app.log for more information", "error")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            if request.content_type == "application/x-www-form-urlencoded":
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                flash("Upload was unsuccessful, please check app.log for more information", "error")
                                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                            else:
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))

                    elif check['method'] == "cydx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, cyclone_path=config['CYDX_LIN_PATH'], cyclone=True)
                        app_log.info(f"{check}")
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), "cydx")
                            if check['status'] == "Success":
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    flash("Upload successful", "info")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    flash("Upload was unsuccessful, please check app.log for more information", "error")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            if request.content_type == "application/x-www-form-urlencoded":
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                flash("Upload was unsuccessful, please check app.log for more information", "error")
                                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                            else:
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                elif check['status'] == "Error":
                    os.remove(dataUpload)
                    if request.content_type == "application/x-www-form-urlencoded":
                        app_log.error({"status": 400, "message": f"{check['message']}"})
                        flash("Upload was unsuccessful, please check app.log for more information", "error")
                        return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                    else:
                        app_log.error({"status": 400, "message": f"{check['message']}"})
                        return (jsonify({"status": 400, "message": f"{check['message']}"}))
                
            elif config['PLATFORM'] == "MacOS":
                check = validate_file(dataUpload, config['CYDX_MAC_PATH'])
                app_log.info(f"{check}")
                if check['status'] == "Success":
                    tempUpload = os.path.join(tempFolder, str(tokenz['fileId']) + ".json")
                    if check['method'] == "spdx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, spdx=True)
                        app_log.info(f"{check}")
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), "spdx")
                            if check['status'] == "Success":
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    flash("Upload successful", "info")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    flash("Upload was unsuccessful, please check app.log for more information", "error")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            if request.content_type == "application/x-www-form-urlencoded":
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                flash("Upload was unsuccessful, please check app.log for more information", "error")
                                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                            else:
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))

                    elif check['method'] == "cydx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, cyclone_path=config['CYDX_MAC_PATH'], cyclone=True)
                        app_log.info(f"{check}")
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), "cydx")
                            if check['status'] == "Success":
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    flash("Upload successful", "info")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.info({"status": 200, "message": "Upload successful", "path": f"{dataUpload}"})
                                    return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                if request.content_type == "application/x-www-form-urlencoded":
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    flash("Upload was unsuccessful, please check app.log for more information", "error")
                                    return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                                else:
                                    app_log.error({"status": 400, "message": f"{check['message']}"})
                                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            if request.content_type == "application/x-www-form-urlencoded":
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                flash("Upload was unsuccessful, please check app.log for more information", "error")
                                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                            else:
                                app_log.error({"status": 400, "message": f"{check['message']}"})
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                elif check['status'] == "Error":
                    os.remove(dataUpload)
                    if request.content_type == "application/x-www-form-urlencoded":
                        app_log.error({"status": 400, "message": f"{check['message']}"})
                        flash("Upload was unsuccessful, please check app.log for more information", "error")
                        return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
                    else:
                        app_log.error({"status": 400, "message": f"{check['message']}"})
                        return (jsonify({"status": 400, "message": f"{check['message']}"}))
        else:
            if request.content_type == "application/x-www-form-urlencoded":
                flash("Invalid file or invalid file extension", "error")
                return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
            else:
                return (jsonify({"status": 404, "message": "Invalid file or invalid file extension"}))
    elif config_check['status'] == "Error":
        if request.content_type == "application/x-www-form-urlencoded":
            app_log.error({"status": 400, "message": config_check['message']})
            flash("Config check failed, check app.log for more information", "error")
            return make_response(redirect(url_for('vendor', vendor_id=vendor_id)))
        else:
            app_log.error({"status": 400, "message": config_check['message']})
            return(jsonify({"status": 400, "message": "Config check failed, check app.log for more information"}))

# -------------------
#   User Management
# -------------------
#
# User management, including user roles, password reset, etc.

# --- Templates ---

@app.route('/admin/user_management')
@jwt_required()
@requires_confirmed_user
@requires_admin
def user_management():
    user_public_id = get_jwt_identity()

    user = User.query.filter_by(public_id=user_public_id).first()
        
    pending_users = User.query.filter_by(confirmed=False).all()
    all_users = User.query.filter_by(confirmed=True).all()
    roles = ["User", "SBOM Admin", "Admin"]
    return render_template('admin/user_management.html', pending_users=pending_users, all_users=all_users, user=user, roles=roles)
    
# --- API ---

@app.route('/api/internal/user/invited_users', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def manage_invited_users():
    action = request.form.get('action')
    user_email = request.form.get('user')
    current_user = User.query.filter_by(public_id=get_jwt_identity()).first()

    # Retrieve the user based on the provided email
    user = User.query.filter_by(email=user_email).first()
    if not user:
        app_log.warning(f"User {current_user.email} failed to confirm or reject a user due to the user not being found.")
        flash("User could not be found.", "error")
        return make_response(redirect(url_for('user_management')))

    if action == 'accept':
        user.confirmed = True
        db.session.commit()
        app_log.info(f"User {user.id} has been confirmed by {current_user.email}.")
        return redirect(url_for('user_management'))
    elif action == 'reject':
        db.session.delete(user)
        db.session.commit()
        app_log.info(f"User {user.id} has been rejected by {current_user.email}.")
        return redirect(url_for('user_management'))
    else:
        app_log.warning(f"User {current_user.email} failed to confirm or reject a user due to an invalid action.")
        flash("Invalid action.", "error")
        return make_response(redirect(url_for('user_management')))
    
@app.route('/api/internal/user/update_roles', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def manage_user_roles():
    roles_data = request.form.to_dict()
    current_user = User.query.filter_by(public_id=get_jwt_identity()).first()

    oneAdminPresent = False
    oneSuperAdminPresent = False
    for key, new_role in roles_data.items():
        if new_role == 'Admin' or new_role == 'Super Admin':
            oneAdminPresent = True
        if new_role == 'Super Admin':
            oneSuperAdminPresent = True

    if not oneAdminPresent:
        app_log.warning(f"User {current_user.email} failed to update user roles due to no admin users being present.")
        flash("There must be at least one admin user.", "error")
        return make_response(redirect(url_for('user_management')))
    
    if not oneSuperAdminPresent:
        app_log.warning(f"User {current_user.email} failed to update user roles due to no super admin users being present.")
        flash("There must be at least one super admin user.", "error")
        return make_response(redirect(url_for('user_management')))

    user_public_id = get_jwt_identity()
    logged_in_user = User.query.filter_by(public_id=user_public_id).first()

    for key, new_role in roles_data.items():
        if new_role not in ['User', 'SBOM Admin', 'Admin', 'Super Admin']:
            app_log.warning(f"User {logged_in_user.email} failed to update user roles due to an invalid role attempting to be set.")
            flash("Invalid role attempting to be set.", "error")
            return make_response(redirect(url_for('user_management')))

        if key.startswith('role['):
            user_id = key.strip('role[').replace(']', '')
            user = User.query.filter_by(id=user_id).first()

            if user.role != 'Super Admin' and new_role == "Super Admin" and logged_in_user.role != 'Super Admin':
                app_log.warning(f"User {logged_in_user.email} failed to update user roles due to unauthorized access.")
                flash("Unauthorized.", "error")
                return make_response(redirect(url_for('user_management')))

            user.role = new_role

            app_log.info(f"User {logged_in_user.email} has updated the role for user {user.email} to {new_role}.")
    
    db.session.commit()

    flash('User roles updated successfully.', 'info')
    return redirect(url_for('user_management'))

@app.route('/api/internal/user/delete_user', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def delete_user():
    data = request.form
    current_user = User.query.filter_by(public_id=get_jwt_identity()).first()

    user_id = data.get('user_id')
    if not user_id:
        app_log.warning(f"User {current_user.email} failed to delete a user due to missing user ID.")
        flash("Missing user ID.", "error")
        return make_response(redirect(url_for('user_management')))

    user = User.query.filter_by(id=user_id).first()
    if not user:
        app_log.warning(f"User {current_user.email} failed to delete a user due to the user ({user_id}) not being found.")
        flash("User not found.", "error")
        return make_response(redirect(url_for('user_management')))
    
    if user.role == 'Super Admin':
        app_log.warning(f"User {current_user.email} failed to delete a user due to attempting to delete the super admin user {user_id}.")
        flash("Cannot delete a super admin user.", "error")
        return make_response(redirect(url_for('user_management')))
    
    admin_users = User.query.filter(or_(User.role == 'Admin', User.role == 'Super Admin')).all()

    if len(admin_users) == 1 and user.role in ['Admin', 'Super Admin']:
        app_log.warning(f"User {current_user.email} failed to delete a user due to attempting to delete the last admin user, {user_id}.")
        flash("There must be at least one admin user.", "error")
        return make_response(redirect(url_for('user_management')))
    
    local_users = User.query.filter_by(sso_user=False).all()
    if len(local_users) == 1 and user.sso_user == False:
        app_log.warning(f"User {current_user.email} failed to delete a user due to attempting to delete the last local user, {user_id}.")
        flash("There must be at least one local user.", "error")
        return make_response(redirect(url_for('user_management')))

    db.session.delete(user)
    db.session.commit()

    app_log.info(f"User {user.email} has been deleted by {current_user.email}.")
    flash(f"User {user.name} has been deleted successfully.", "info")
    return redirect(url_for('user_management'))

@app.route('/api/internal/user/reset_password', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def reset_password():
    data = request.form
    current_user = User.query.filter_by(public_id=get_jwt_identity()).first()

    user_id = data.get('user_id')
    new_password = data.get('new_password')

    if not user_id or not new_password:
        app_log.warning(f"User {current_user.email} failed to reset a password due to missing user ID or new password.")
        flash("Missing a new password.", "error")
        return make_response(redirect(url_for('user_management')))
    
    if current_user.sso_user:
        app_log.warning(f"User {current_user.email} failed to reset a password due to being an SSO user.")
        flash("Cannot reset password for SSO users.", "error")
        return make_response(redirect(url_for('user_management')))
    
    if (len(new_password) < 12 or not re.search("[a-z]", new_password) or not re.search("[A-Z]", new_password) or not re.search("[0-9]", new_password) or not re.search("[!@#$%^&*(),.?\":{}|<>]", new_password)):
        app_log.warning(f"User {current_user.email} failed to reset a password for {user_id} due to an invalid password.")
        flash("The entered password does not meet the requirements of:<br>- 12+ characters<br>- At least one uppercase and lowecase letter<br>- At least one number<br>- At least one special character<br><br>Please try again.", "error")
        response = make_response(redirect(url_for('user_management')))
        return response
    
    user_id = int(user_id)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        app_log.warning(f"User {current_user.email} failed to reset a password for {user_id} due to the user not being found.")
        flash("User not found.", "error")
        return make_response(redirect(url_for('user_management')))
    
    user_public_id = get_jwt_identity()
    logged_in_user = User.query.filter_by(public_id=user_public_id).first()

    if user.role == 'Super Admin' and logged_in_user.role != 'Super Admin':
        app_log.warning(f"User {current_user.email} failed to reset a password for {user_id} due to unauthorized access.")
        flash("Unauthorized.", "error")
        return make_response(redirect(url_for('user_management')))

    user.password = generate_password_hash(new_password, "pbkdf2")

    db.session.commit()

    app_log.info(f"Password for user {user.name} has been reset by {current_user.email}.")
    flash(f"Password for {user.name} has been reset successfully.", "info")
    return make_response(redirect(url_for('user_management')))


# ---------------------------------
#   Authencation and Authorization
# ---------------------------------
#
# login, register, sso settings, token management, etc.

# -- Templates --

@app.route('/login')
@jwt_required(optional=True)
def login():
    current_user = get_jwt_identity()

    if current_user and current_user != None:
        user = User.query.filter_by(public_id=current_user).first()

        if user and user.confirmed:
            return redirect(url_for('index'))

    return render_template('login.html')
    
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/logout', methods=['GET'])
@jwt_required()
def logout():
    current_user = User.query.filter_by(public_id=get_jwt_identity()).first()
    app_log.info(f"User {current_user.email} has logged out.")

    response = make_response(redirect(url_for('login')))

    response.set_cookie('access_token_cookie', '', expires=0, path='/')
    unset_jwt_cookies(response)

    return response

# -- SSO routes --

@app.route("/sso-login")
def login_test():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True),
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()

    user = User.query.filter_by(email=(token["userinfo"]["email"]).lower()).first()

    if user:
        if not user.sso_user:
            flash("User already exists locally. Please log in or remove the account.", "error")
            return make_response(redirect(url_for('login')))

    if not user:
        user = User(public_id=str(uuid.uuid4()), name=token["userinfo"]["name"], email=(token["userinfo"]["email"]).lower(), role="User", confirmed=True, sso_user=True)
        db.session.add(user)
        db.session.commit()

    if user.name != token["userinfo"]["name"]:
        user.name = token["userinfo"]["name"]
        db.session.commit()

    access_token = create_access_token(identity=user.public_id, fresh=True)
    response = make_response(redirect(url_for('index')))
    set_access_cookies(response, access_token)

    return response


# -- API routes --

@app.route('/api/internal/user/login', methods=['POST'])
def login_user():
    auth = request.form

    if not auth or not auth.get('email') or not auth.get('password'):
        app_log.warning(f"User failed to log in due to missing email or password.")
        flash("Missing email or password.", "error")
        return redirect(url_for('login'))
    
    user = User.query.filter_by(email=(auth.get('email')).lower()).first()

    if user.confirmed == False:
        app_log.warning(f"User {auth.get('email')} failed to log in due to the user not being confirmed.")
        flash("Your account has not been confirmed. Please wait until your account is confirmed by an Admin.", "error")
        return redirect(url_for('login'))
    
    if user.sso_user:
        app_log.warning(f"User {auth.get('email')} failed to log in due to being an SSO user.")
        flash("Cannot log in with local credentials for an SSO user.", "error")
        return redirect(url_for('login'))

    if not user or not check_password_hash(user.password, auth.get('password')):
        app_log.warning(f"User {auth.get('email')} failed to log in due to the user not being found or the password being wrong.")
        flash("User does not exist or password is wrong.", "error")
        return redirect(url_for('login'))

    # Create JWT token
    access_token = create_access_token(identity=user.public_id, fresh=True)
    
    # Instead of returning a JSON response, create a redirect response
    response = make_response(redirect(url_for('index')))
    # Set the JWT in cookies
    set_access_cookies(response, access_token)

    app_log.info(f"User {user.name} has logged in.")

    return response

@app.route('/api/internal/user/register', methods=['POST'])
def signup_user():
    data = request.form

    name, email = data.get('name'), (data.get('email')).lower()
    password, confirm_password = data.get('password'), data.get('confirm_password')

    if (password != confirm_password):
        app_log.warning(f"{name}, {email} failed user registration due to mismatched password.")
        flash("Passwords do not match.", "error")
        response = make_response(redirect(url_for('register')))
        return response
    
    if (len(password) < 12 or not re.search("[a-z]", password) or not re.search("[A-Z]", password) or not re.search("[0-9]", password) or not re.search("[!@#$%^&*(),.?\":{}|<>]", password)):
        app_log.warning(f"{name}, {email} failed user registration due to an invalid password.")
        flash("The entered password does not meet the requirements. Please try again.", "error")
        response = make_response(redirect(url_for('register')))
        return response
  
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(public_id=str(uuid.uuid4()), name=name, email=email, password=generate_password_hash(password, "pbkdf2"), role="User")
        db.session.add(user)
        db.session.commit()

        app_log.info(f"User {user.name}, {user.email} has been registered.")
        flash("User created successfully. Please wait until your account is confirmed by an Admin.", "info")
        response = make_response(redirect(url_for('login')))

        return response
    else:
        flash("User already exists. Please log in.", "error")
        app_log.warning(f"{name}, {email} failed user registration due to an existing user.")
        response = make_response(redirect(url_for('register')))
        return response

    
# -- JWT and Cookie management --

@jwt.expired_token_loader
def my_expired_token_callback(jwt_header, jwt_payload):
    flash('Your session has expired. Please log in again.', 'error')
    response = make_response(redirect(url_for('login')))  # Redirect to login or another page
    unset_jwt_cookies(response)  # Clear the JWT cookies
    response.set_cookie('access_token_cookie', '', expires=0)
    response.set_cookie('refresh_token_cookie', '', expires=0)
    return response

# Unauthorized handler
@jwt.unauthorized_loader
def unauthorized_callback(callback):
    # Redirect to the 404 page
    return redirect(url_for("not_found"))

# ----------------------------
#   Configuration Management
# ----------------------------
#
# Configuration management, including SSO settings, integrations, etc.

def update_env_file(key, value):
    """Safely update a .env file with a new key-value pair."""
    # Specify the path to your .env file
    env_path = './.env'
    set_key(env_path, key, value)

@app.route('/admin/settings', methods=['GET'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def settings():
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()

    current_settings = dotenv_values(".env")
    return render_template('admin/settings.html', 
                           user=user, 
                           API_KEY_LENGTH=len(current_settings.get('THIRD_PARTY_TRUST_API_KEY')),
                           REQUIREMENT_LABEL_ID=current_settings.get('SBOM_REQUIREMENT_LABEL_ID'))

@app.route('/admin/sso-setup', methods=['GET', 'POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def sso_setup():
    user_public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=user_public_id).first()


    # Get current settings to pre-fill the form
    current_settings = dotenv_values(".env")
    return render_template('admin/sso_setup.html', 
                           user=user, 
                           OIDC_PROVIDER=current_settings.get('OIDC_PROVIDER'), 
                           CLIENT_ID=current_settings.get('AUTH0_CLIENT_ID', ''),
                           CLIENT_SECRET_LENGTH=len(current_settings.get('AUTH0_CLIENT_SECRET', '')),
                           PROVIDER_DOMAIN=current_settings.get('AUTH0_DOMAIN', ''))

@app.route('/api/internal/configuration/sso', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def configure_sso():
        OIDC_PROVIDER = request.form.get('OIDC_PROVIDER')
        CLIENT_ID = request.form.get('CLIENT_ID')
        CLIENT_SECRET = request.form.get('CLIENT_SECRET')
        PROVIDER_DOMAIN = request.form.get('PROVIDER_DOMAIN')

        if not OIDC_PROVIDER or not CLIENT_ID:
            flash('Not all fields have been filled in.', 'error')
            return redirect(url_for('sso_setup'))

        # Update .env file safely
        update_env_file('OIDC_PROVIDER', OIDC_PROVIDER)
        update_env_file('AUTH0_CLIENT_ID', CLIENT_ID)
        update_env_file('AUTH0_DOMAIN', PROVIDER_DOMAIN)
        if CLIENT_SECRET:
            update_env_file('AUTH0_CLIENT_SECRET', CLIENT_SECRET)

        load_dotenv(override=True)
        

        flash('SSO settings updated successfully.', 'info')
        return redirect(url_for('sso_setup'))

@app.route('/api/internal/configuration/logo/upload', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@requires_admin
def update_logo():
        pass

@app.route('/api/internal/configuration/third_party_trust', methods=['POST'])
@jwt_required()
@requires_confirmed_user
@block_read_only
def update_third_party_trust_integration():
    pass

def syncThirdPartyTrustVendors():
    print("Fetching vendors from ThirdPartyTrust's API...")

    url = "https://api.thirdpartytrust.com/api/v2/connections.actives"

    payload = {}
    headers = {
    'Authorization': f'Token {os.getenv("THIRD_PARTY_TRUST_API_KEY")}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code == 200:
        vendors = json.loads(response.text)
        for vendor in vendors:
            vendorName = vendor['company']['name']

            # Check if vendor already exists
            with app.app_context():
                existingVendor = Vendor.query.filter_by(integration_id=vendor['company']['uuid']).first()

            if not existingVendor:
                try:
                    incomingLabelUUIDs = vendor['incoming']['label_uuids']
                except:
                    incomingLabelUUIDs = []

                try:
                    outgoingLabelUUIDs = vendor['outgoing']['label_uuids']
                except:
                    outgoingLabelUUIDs = []

                if (os.getenv('SBOM_REQUIREMENT_LABEL_ID') in incomingLabelUUIDs or os.getenv('SBOM_REQUIREMENT_LABEL_ID') in outgoingLabelUUIDs):
                    # Add new vendor
                    with app.app_context():
                        newVendor = Vendor(name=vendorName, integration_id=vendor['company']['uuid'])
                        db.session.add(newVendor)
                        db.session.commit()
                        print(f"Added new vendor: {vendorName}")
                else:
                    print(f"Vendor is not required to provide a SBOM: {vendorName}")
            else:
                print(f"Vendor already exists: {vendorName}")
    else:
        print("Failed to fetch vendors")

# -----------
#   Generic
# -----------
        
@app.route('/404.html')
def not_found():
    return render_template('404.html')

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=syncThirdPartyTrustVendors, trigger="interval", minutes=45)
    scheduler.start()

    app.run(debug=False, port=5000, use_reloader=True)