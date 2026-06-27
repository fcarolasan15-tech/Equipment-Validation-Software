import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.audit import AuditEvent
from app.services.audit_logger import log_event
import app.models  # noqa


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_log_event_basic(db):
    event = log_event(db, "TEST_EVENT", user_id=1, entity_type="Asset", entity_id=42,
                       description="Test description")
    db.commit()
    fetched = db.query(AuditEvent).filter_by(event_type="TEST_EVENT").first()
    assert fetched is not None
    assert fetched.entity_id == 42
    assert fetched.description == "Test description"


def test_log_event_with_values(db):
    log_event(db, "RISK_UPDATED", user_id=1, entity_type="Asset", entity_id=1,
               old_values={"risk_score": 4}, new_values={"risk_score": 32})
    db.commit()
    ev = db.query(AuditEvent).filter_by(event_type="RISK_UPDATED").first()
    assert ev.old_values["risk_score"] == 4
    assert ev.new_values["risk_score"] == 32


def test_multiple_events(db):
    for i in range(5):
        log_event(db, f"EVENT_{i}", entity_type="Project", entity_id=1)
    db.commit()
    count = db.query(AuditEvent).count()
    assert count == 5
