import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TemplateTypeEnum(str, enum.Enum):
    FFSR01 = "F-FSR-01"
    FFSR02 = "F-FSR-02"
    FFSR03 = "F-FSR-03"
    FFSR04 = "F-FSR-04"
    FFSR05 = "F-FSR-05"
    FFSR06 = "F-FSR-06"


class TemplateStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    OBSOLETE = "OBSOLETE"


class TemplateVersion(Base):
    __tablename__ = "template_versions"

    id = Column(Integer, primary_key=True, index=True)
    form_code = Column(Enum(TemplateTypeEnum), nullable=False)
    version = Column(String(20), nullable=False)
    title = Column(String(300), nullable=False)
    status = Column(Enum(TemplateStatusEnum), default=TemplateStatusEnum.DRAFT)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)

    files = relationship("TemplateFile", back_populates="template_version")
    field_maps = relationship("TemplateFieldMap", back_populates="template_version")
    records = relationship("ValidationRecord", back_populates="template_version")


class TemplateFile(Base):
    __tablename__ = "template_files"

    id = Column(Integer, primary_key=True, index=True)
    template_version_id = Column(Integer, ForeignKey("template_versions.id"), nullable=False)
    filename = Column(String(300), nullable=False)
    file_type = Column(String(10), nullable=False)  # docx / xlsx
    vault_path = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=False, unique=True)
    file_size = Column(Integer, nullable=True)
    baseline_pdf_path = Column(String(500), nullable=True)
    baseline_pdf_hash = Column(String(64), nullable=True)
    baseline_page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    template_version = relationship("TemplateVersion", back_populates="files")


class TemplateFieldMap(Base):
    __tablename__ = "template_field_maps"

    id = Column(Integer, primary_key=True, index=True)
    template_version_id = Column(Integer, ForeignKey("template_versions.id"), nullable=False)
    source_file_hash = Column(String(64), nullable=False)
    field_key = Column(String(100), nullable=False)
    label = Column(String(200), nullable=True)
    field_type = Column(String(50), default="text")  # text/checkbox/date/select
    cell_ref = Column(String(50), nullable=True)     # for XLSX: e.g. "B5" or named range
    is_required = Column(Boolean, default=False)
    default_value = Column(String(500), nullable=True)
    options = Column(JSON, nullable=True)            # for select fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    template_version = relationship("TemplateVersion", back_populates="field_maps")
