import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ProjectStageEnum(str, enum.Enum):
    INITIATION = "INITIATION"
    DQ = "DQ"
    PROTOCOL = "PROTOCOL"
    IQ = "IQ"
    OQ = "OQ"
    PQ = "PQ"
    REPORT = "REPORT"
    RELEASED = "RELEASED"


class ProjectStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ValidationProject(Base):
    __tablename__ = "validation_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_number = Column(String(50), nullable=False, unique=True)
    title = Column(String(300), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_stage = Column(Enum(ProjectStageEnum), default=ProjectStageEnum.INITIATION)
    status = Column(Enum(ProjectStatusEnum), default=ProjectStatusEnum.ACTIVE)

    # Qualification scope (from risk matrix)
    scope_iq = Column(String(10), default="REQUIRED")   # REQUIRED / OPTIONAL / NOT_REQUIRED
    scope_oq = Column(String(10), default="REQUIRED")
    scope_pq = Column(String(10), default="REQUIRED")
    scope_justification = Column(Text, nullable=True)

    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    target_completion = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    asset = relationship("Asset", back_populates="projects")
    site = relationship("Site", back_populates="projects")
    owner = relationship("User", foreign_keys=[owner_id])
    records = relationship("ValidationRecord", back_populates="project")
