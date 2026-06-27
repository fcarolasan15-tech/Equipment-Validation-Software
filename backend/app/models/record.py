import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RecordStageEnum(str, enum.Enum):
    DQ = "DQ"
    PROTOCOL = "PROTOCOL"
    IQ = "IQ"
    OQ = "OQ"
    PQ = "PQ"
    REPORT = "REPORT"


class RecordStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ValidationRecord(Base):
    __tablename__ = "validation_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("validation_projects.id"), nullable=False)
    template_version_id = Column(Integer, ForeignKey("template_versions.id"), nullable=False)
    stage = Column(Enum(RecordStageEnum), nullable=False)
    status = Column(Enum(RecordStatusEnum), default=RecordStatusEnum.DRAFT)
    document_number = Column(String(100), nullable=True)
    revision = Column(String(10), default="00")

    field_data = Column(JSON, nullable=True)  # filled form values

    prepared_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    prepared_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    current_pdf_path = Column(String(500), nullable=True)
    current_pdf_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("ValidationProject", back_populates="records")
    template_version = relationship("TemplateVersion", back_populates="records")
    prepared_by = relationship("User", foreign_keys=[prepared_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    versions = relationship("RecordVersion", back_populates="record")
    execution_items = relationship("ExecutionItem", back_populates="record")
    signatures = relationship("Signature", back_populates="record")
    attachments = relationship("Attachment", back_populates="record")
    render_jobs = relationship("RenderJob", back_populates="record")


class RecordVersion(Base):
    __tablename__ = "record_versions"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("validation_records.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    field_data_snapshot = Column(JSON, nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    change_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("ValidationRecord", back_populates="versions")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
