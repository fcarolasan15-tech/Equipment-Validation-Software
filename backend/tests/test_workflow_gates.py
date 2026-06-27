import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.project import ValidationProject, ProjectStageEnum
from app.models.record import ValidationRecord, RecordStatusEnum, RecordStageEnum
from app.models.template import TemplateVersion, TemplateTypeEnum, TemplateStatusEnum
from app.models.organization import Organization, Site
from app.models.user import User, Role, RoleEnum
from app.models.asset import Asset
from app.services.workflow import can_advance_to, advance_stage, WorkflowError, get_recommended_scope
from app.services.auth import hash_password
import app.models  # noqa


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def project(db):
    org = Organization(name="Test Org", short_name="TST")
    db.add(org)
    db.flush()
    site = Site(organization_id=org.id, name="Test Site", code="TST")
    db.add(site)
    db.flush()
    user = User(email="test@test.com", full_name="Test User",
                hashed_password=hash_password("test"), must_change_password=False)
    db.add(user)
    db.flush()
    asset = Asset(site_id=site.id, asset_tag="EQ-001", equipment_name="Test Equipment",
                  metric_food_safety=1, metric_downtime=1, metric_age=1, metric_pm_conformance=1,
                  metric_calibration=1, metric_validation_status=1, metric_spare_parts=1,
                  metric_safety_systems=1)
    asset.compute_risk()
    db.add(asset)
    db.flush()
    tv = TemplateVersion(form_code=TemplateTypeEnum.FFSR01, version="01",
                          title="Test Template", status=TemplateStatusEnum.APPROVED)
    db.add(tv)
    db.flush()
    proj = ValidationProject(
        project_number="VP-2025-0001", title="Test Project",
        asset_id=asset.id, site_id=site.id, owner_id=user.id,
        current_stage=ProjectStageEnum.INITIATION,
    )
    db.add(proj)
    db.commit()
    return proj, user, tv


def test_can_advance_initiation_to_dq(db, project):
    proj, _, _ = project
    ok, reason = can_advance_to(db, proj, ProjectStageEnum.DQ)
    assert ok, reason


def test_cannot_skip_stages(db, project):
    proj, _, _ = project
    ok, reason = can_advance_to(db, proj, ProjectStageEnum.PROTOCOL)
    assert not ok
    assert "skip" in reason.lower()


def test_cannot_advance_to_protocol_without_approved_dq(db, project):
    proj, user, tv = project
    advance_stage(db, proj, ProjectStageEnum.DQ)
    dq_record = ValidationRecord(
        project_id=proj.id, template_version_id=tv.id,
        stage=RecordStageEnum.DQ, status=RecordStatusEnum.DRAFT,
        prepared_by_id=user.id,
    )
    db.add(dq_record)
    db.commit()

    ok, reason = can_advance_to(db, proj, ProjectStageEnum.PROTOCOL)
    assert not ok
    assert "APPROVED" in reason


def test_advance_to_protocol_with_approved_dq(db, project):
    proj, user, tv = project
    advance_stage(db, proj, ProjectStageEnum.DQ)
    dq_record = ValidationRecord(
        project_id=proj.id, template_version_id=tv.id,
        stage=RecordStageEnum.DQ, status=RecordStatusEnum.APPROVED,
        prepared_by_id=user.id,
    )
    db.add(dq_record)
    db.commit()

    ok, reason = can_advance_to(db, proj, ProjectStageEnum.PROTOCOL)
    assert ok, reason


def test_workflow_error_on_invalid_advance(db, project):
    proj, _, _ = project
    with pytest.raises(WorkflowError):
        advance_stage(db, proj, ProjectStageEnum.PROTOCOL)


def test_risk_scope_recommendation():
    scope = get_recommended_scope("HIGH", "DIRECT")
    assert scope["iq"] == "REQUIRED"
    assert scope["oq"] == "REQUIRED"
    assert scope["pq"] == "REQUIRED"


def test_risk_scope_no_impact():
    scope = get_recommended_scope("HIGH", "NONE")
    assert scope["iq"] == "NOT_REQUIRED"


def test_risk_score_computation():
    asset = Asset(site_id=1, asset_tag="X", equipment_name="X",
                  metric_food_safety=2, metric_downtime=2, metric_age=1,
                  metric_pm_conformance=1, metric_calibration=1,
                  metric_validation_status=1, metric_spare_parts=1,
                  metric_safety_systems=1)
    score = asset.compute_risk()
    assert score == 4
    assert asset.risk_level.value == "LOW"


def test_high_risk_score():
    asset = Asset(site_id=1, asset_tag="Y", equipment_name="Y",
                  metric_food_safety=2, metric_downtime=2, metric_age=2,
                  metric_pm_conformance=2, metric_calibration=1,
                  metric_validation_status=1, metric_spare_parts=1,
                  metric_safety_systems=1)
    score = asset.compute_risk()
    assert score == 16
    assert asset.risk_level.value == "MEDIUM"
