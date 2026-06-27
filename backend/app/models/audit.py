import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RenderStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("validation_records.id"), nullable=False)
    triggered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(RenderStatusEnum), default=RenderStatusEnum.PENDING)
    source_file_path = Column(String(500), nullable=True)
    output_pdf_path = Column(String(500), nullable=True)
    pdf_hash = Column(String(64), nullable=True)
    page_count = Column(Integer, nullable=True)
    diff_score = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    record = relationship("ValidationRecord", back_populates="render_jobs")
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("validation_records.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(300), nullable=False)
    content_type = Column(String(100), nullable=True)
    vault_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    sha256_hash = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("ValidationRecord", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
