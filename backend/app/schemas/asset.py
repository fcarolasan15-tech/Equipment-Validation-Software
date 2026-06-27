from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssetCreate(BaseModel):
    site_id: int
    asset_tag: str
    equipment_name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    department: Optional[str] = None
    department_code: Optional[str] = None
    location: Optional[str] = None
    year_installed: Optional[int] = None


class RiskAssessmentUpdate(BaseModel):
    metric_food_safety: int = 1
    metric_downtime: int = 1
    metric_age: int = 1
    metric_pm_conformance: int = 1
    metric_calibration: int = 1
    metric_validation_status: int = 1
    metric_spare_parts: int = 1
    metric_safety_systems: int = 1
    urs_impact: Optional[str] = None


class AssetOut(BaseModel):
    id: int
    site_id: int
    asset_tag: str
    equipment_name: str
    model: Optional[str]
    manufacturer: Optional[str]
    serial_number: Optional[str]
    department: Optional[str]
    department_code: Optional[str]
    location: Optional[str]
    year_installed: Optional[int]
    risk_score: Optional[int]
    risk_level: Optional[str]
    urs_impact: Optional[str]
    metric_food_safety: int
    metric_downtime: int
    metric_age: int
    metric_pm_conformance: int
    metric_calibration: int
    metric_validation_status: int
    metric_spare_parts: int
    metric_safety_systems: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
