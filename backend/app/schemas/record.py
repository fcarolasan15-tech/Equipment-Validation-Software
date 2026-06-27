from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class RecordCreate(BaseModel):
    project_id: int
    template_version_id: int
    stage: str
    document_number: Optional[str] = None


class RecordDataUpdate(BaseModel):
    field_data: dict[str, Any]
    change_reason: Optional[str] = None


class RecordOut(BaseModel):
    id: int
    project_id: int
    template_version_id: int
    stage: str
    status: str
    document_number: Optional[str]
    revision: str
    field_data: Optional[dict]
    prepared_by_id: Optional[int]
    reviewed_by_id: Optional[int]
    approved_by_id: Optional[int]
    prepared_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    approved_at: Optional[datetime]
    current_pdf_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SignRequest(BaseModel):
    password: str
    meaning: Optional[str] = None


class DeviationCreate(BaseModel):
    record_id: int
    execution_item_id: Optional[int] = None
    description: str
    severity: str
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    is_blocking: bool = False


class DeviationOut(BaseModel):
    id: int
    record_id: int
    deviation_number: str
    description: str
    severity: str
    status: str
    root_cause: Optional[str]
    corrective_action: Optional[str]
    raised_by_id: int
    raised_at: datetime
    is_blocking: bool

    model_config = {"from_attributes": True}


class ExecutionItemUpdate(BaseModel):
    actual_result: Optional[str] = None
    status: str
    notes: Optional[str] = None
