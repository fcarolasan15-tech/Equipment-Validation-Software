import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class URSImpactEnum(str, enum.Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    SAFETY = "SAFETY"
    NONE = "NONE"


class RiskLevelEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    asset_tag = Column(String(100), nullable=False, unique=True)
    equipment_name = Column(String(300), nullable=False)
    model = Column(String(200), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    serial_number = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)
    department_code = Column(String(10), nullable=True)
    location = Column(String(200), nullable=True)
    year_installed = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Risk assessment metrics (1=conforming, 2=non-conforming)
    metric_food_safety = Column(Integer, default=1)
    metric_downtime = Column(Integer, default=1)
    metric_age = Column(Integer, default=1)
    metric_pm_conformance = Column(Integer, default=1)
    metric_calibration = Column(Integer, default=1)
    metric_validation_status = Column(Integer, default=1)
    metric_spare_parts = Column(Integer, default=1)
    metric_safety_systems = Column(Integer, default=1)

    risk_score = Column(Integer, default=1)
    risk_level = Column(Enum(RiskLevelEnum), nullable=True)
    urs_impact = Column(Enum(URSImpactEnum), nullable=True)

    site = relationship("Site", back_populates="assets")
    projects = relationship("ValidationProject", back_populates="asset")

    def compute_risk(self):
        score = (
            (self.metric_food_safety or 1) *
            (self.metric_downtime or 1) *
            (self.metric_age or 1) *
            (self.metric_pm_conformance or 1) *
            (self.metric_calibration or 1) *
            (self.metric_validation_status or 1) *
            (self.metric_spare_parts or 1) *
            (self.metric_safety_systems or 1)
        )
        self.risk_score = score
        if score <= 4:
            self.risk_level = RiskLevelEnum.LOW
        elif score <= 16:
            self.risk_level = RiskLevelEnum.MEDIUM
        else:
            self.risk_level = RiskLevelEnum.HIGH
        return score
