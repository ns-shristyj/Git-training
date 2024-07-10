from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

class Vendor(db.Model):
    __tablename__ = 'vendors'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    integration_id = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Foreign key to User

    # Relationship to User
    created_by = relationship('User', backref='vendors_created', foreign_keys=[created_by_id])

    # Relationship to components
    components = relationship("Component", backref="vendors", lazy=True)

class Component(db.Model):
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    version = db.Column(db.String(100))
    vcs = db.Column(db.String(255))
    license = db.Column(db.String(255))
    package_url = db.Column(db.String(255))
    hash = db.Column(db.String(255))
    hash_type = db.Column(db.String(20))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))  # Link to SBOM submission

    # Relationship to vulnerabilities
    vulnerabilities = relationship("Vulnerability", backref="components", lazy=True)

class Vulnerability(db.Model):
    __tablename__ = 'vulnerabilities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vulnerability_id = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(50))
    cwe = db.Column(db.String(50))
    cvss_score = db.Column(db.Integer)
    cvss_type = db.Column(db.String(50))
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(70), unique=True)
    password = db.Column(db.String(80))
    confirmed = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(80), default=False)
    sso_user = db.Column(db.Boolean, default=False)
