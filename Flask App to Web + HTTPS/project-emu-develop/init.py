# initialize_db.py
from models import db, User, Vendor, Component, Vulnerability
from dotenv import load_dotenv
import os, uuid
from app import app
from werkzeug.security import generate_password_hash

load_dotenv()

def initialize_database():
    with app.app_context():
        db.create_all()

        # Assuming test_company.id is populated after commit
        test_user1 = User(name="Admin User", email="nskp-gis-seceng@netskope.com", password=generate_password_hash(os.getenv("admin_pass"), "pbkdf2"), confirmed=True, role="Super Admin", public_id=str(uuid.uuid4()))
        db.session.add(test_user1)
        db.session.commit()

        for i in range(0,10):
            if i % 4 == 0:
                new_vendor = Vendor(name=f"Vendor {i}", created_by=test_user1, active=False)
            else:
                new_vendor = Vendor(name=f"Vendor {i}", created_by=test_user1)
            
            db.session.add(new_vendor)
            db.session.commit()

            for j in range(0,40 + (i * 6)):
                new_component = Component(name=f"Component {j}", description="A description.", version=f"1.{j}.0", vcs = f"https://github.com/project/{j}.git/", license="MIT", package_url=f"https://pypi.org/project/{j}/", hash=f"hash{j}", hash_type="SHA256", vendor_id=new_vendor.id)
                
                db.session.add(new_component)
                db.session.commit()

                for k in range(0, 8):
                    severities = ["Low", "Medium", "High", "Critical"]
                    new_vulnerability = Vulnerability(vulnerability_id=f"Vuln {k}", name=f"Vulnerability {k}", severity=severities[k % 4], cwe="CWE-123", cvss_score=10, cvss_type="CVSSv3", component_id=new_component.id)
                    
                    db.session.add(new_vulnerability)
                    db.session.commit()

if __name__ == '__main__':
    initialize_database()
    print("Database initialized and test data added.")
