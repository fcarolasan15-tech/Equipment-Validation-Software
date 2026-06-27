"""
Run once to seed the database with initial data.
Usage: python -m app.seed.seed
"""
from app.database import SessionLocal, engine, Base
from app.models.user import User, Role, UserRole, RoleEnum
from app.models.organization import Organization, Site
from app.models.asset import Asset
from app.services.auth import hash_password
import app.models  # noqa


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Organization).first():
            print("Already seeded.")
            return

        org = Organization(name="Del Monte Philippines Inc.", short_name="DMPI")
        db.add(org)
        db.flush()

        site = Site(organization_id=org.id, name="Bugo Plant", code="BGP")
        db.add(site)
        db.flush()

        for role_enum in RoleEnum:
            db.add(Role(name=role_enum))
        db.flush()

        admin_role = db.query(Role).filter_by(name=RoleEnum.ADMIN).first()
        fsqr_role = db.query(Role).filter_by(name=RoleEnum.FSQR_MANAGER).first()
        ve_role = db.query(Role).filter_by(name=RoleEnum.VALIDATION_ENGINEER).first()

        admin = User(
            organization_id=org.id, site_id=site.id,
            email="admin@dmpi.com.ph",
            full_name="System Administrator",
            department="Corporate Quality Management",
            department_code="FSR",
            position="System Admin",
            hashed_password=hash_password("changeme123"),
            must_change_password=True,
        )
        db.add(admin)
        db.flush()
        db.add(UserRole(user_id=admin.id, role_id=admin_role.id))

        engineer = User(
            organization_id=org.id, site_id=site.id,
            email="ve@dmpi.com.ph",
            full_name="[Validation Engineer]",
            department="Corporate Quality Management",
            department_code="FSR",
            position="Validation Engineer",
            hashed_password=hash_password("changeme123"),
            must_change_password=True,
        )
        db.add(engineer)
        db.flush()
        db.add(UserRole(user_id=engineer.id, role_id=ve_role.id))

        sample_asset = Asset(
            site_id=site.id,
            asset_tag="EQ-BGP-001",
            equipment_name="[Equipment Name]",
            model="[Model]",
            manufacturer="[Manufacturer]",
            serial_number="[Serial Number]",
            department="Solids Processing Department",
            department_code="SPC",
            location="Cook Room",
            year_installed=2015,
            metric_food_safety=2,
            metric_downtime=1,
            metric_age=2,
            metric_pm_conformance=1,
            metric_calibration=1,
            metric_validation_status=2,
            metric_spare_parts=1,
            metric_safety_systems=1,
        )
        sample_asset.compute_risk()
        db.add(sample_asset)

        db.commit()
        print("Seed complete.")
        print("  Admin: admin@dmpi.com.ph / changeme123")
        print("  Engineer: ve@dmpi.com.ph / changeme123")
        print("  Note: First login forces password change.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
