from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    title: str
    asset_id: int
    site_id: int
    scope_iq: str = "REQUIRED"
    scope_oq: str = "REQUIRED"
    scope_pq: str = "REQUIRED"
    scope_justification: Optional[str] = None
    target_completion: Optional[datetime] = None
    notes: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    project_number: str
    title: str
    asset_id: int
    site_id: int
    owner_id: int
    current_stage: str
    status: str
    scope_iq: str
    scope_oq: str
    scope_pq: str
    scope_justification: Optional[str]
    initiated_at: datetime
    target_completion: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class StageAdvanceRequest(BaseModel):
    target_stage: str
