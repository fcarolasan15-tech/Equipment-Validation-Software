from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.routers.deps import get_current_user, require_admin
from app.models.user import User
from app.models.template import TemplateVersion, TemplateFile, TemplateFieldMap, TemplateStatusEnum, TemplateTypeEnum
from app.services.template_registry import register_template_file, compute_sha256
from app.services.audit_logger import log_event
from app.config import settings

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateVersionCreate(BaseModel):
    form_code: str
    version: str
    title: str
    notes: Optional[str] = None


class FieldMapCreate(BaseModel):
    field_key: str
    label: str
    field_type: str = "text"
    cell_ref: Optional[str] = None
    is_required: bool = False
    default_value: Optional[str] = None
    options: Optional[list] = None


@router.get("")
def list_templates(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    versions = db.query(TemplateVersion).all()
    result = []
    for tv in versions:
        result.append({
            "id": tv.id, "form_code": tv.form_code, "version": tv.version,
            "title": tv.title, "status": tv.status, "created_at": tv.created_at,
            "file_count": len(tv.files),
        })
    return result


@router.post("", status_code=201)
def create_template_version(body: TemplateVersionCreate,
                             db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        form_code = TemplateTypeEnum(body.form_code)
    except ValueError:
        raise HTTPException(400, f"Unknown form code: {body.form_code}")

    tv = TemplateVersion(form_code=form_code, version=body.version, title=body.title, notes=body.notes)
    db.add(tv)
    log_event(db, "TEMPLATE_VERSION_CREATED", user_id=admin.id, entity_type="TemplateVersion",
               description=f"{body.form_code} v{body.version}")
    db.commit()
    db.refresh(tv)
    return {"id": tv.id, "form_code": tv.form_code, "version": tv.version}


@router.post("/{version_id}/upload-file", status_code=201)
async def upload_template_file(version_id: int, file: UploadFile = File(...),
                                db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    tv = db.query(TemplateVersion).filter_by(id=version_id).first()
    if not tv:
        raise HTTPException(404, "Template version not found")

    import aiofiles
    tmp_path = Path("/tmp") / file.filename
    content = await file.read()
    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(content)

    tf = register_template_file(db, version_id, tmp_path, file.filename)
    log_event(db, "TEMPLATE_FILE_UPLOADED", user_id=admin.id, entity_type="TemplateFile",
               entity_id=tf.id, description=file.filename)
    db.commit()
    return {"id": tf.id, "sha256": tf.sha256_hash, "vault_path": tf.vault_path}


@router.post("/{version_id}/approve")
def approve_template(version_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    tv = db.query(TemplateVersion).filter_by(id=version_id).first()
    if not tv:
        raise HTTPException(404, "Template version not found")

    # Supersede old approved versions of same form
    db.query(TemplateVersion).filter(
        TemplateVersion.form_code == tv.form_code,
        TemplateVersion.status == TemplateStatusEnum.APPROVED,
        TemplateVersion.id != version_id,
    ).update({"status": TemplateStatusEnum.SUPERSEDED})

    tv.status = TemplateStatusEnum.APPROVED
    tv.approved_by_id = admin.id
    tv.approved_at = datetime.now(timezone.utc)
    log_event(db, "TEMPLATE_APPROVED", user_id=admin.id, entity_type="TemplateVersion", entity_id=version_id)
    db.commit()
    return {"status": tv.status}


@router.get("/{version_id}/field-map")
def get_field_map(version_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    fields = db.query(TemplateFieldMap).filter_by(template_version_id=version_id).all()
    return fields


@router.post("/{version_id}/field-map", status_code=201)
def add_field_map(version_id: int, body: FieldMapCreate,
                  db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    tv = db.query(TemplateVersion).filter_by(id=version_id).first()
    if not tv:
        raise HTTPException(404, "Template version not found")

    tf = db.query(TemplateFile).filter_by(template_version_id=version_id).first()
    source_hash = tf.sha256_hash if tf else ""

    field = TemplateFieldMap(
        template_version_id=version_id,
        source_file_hash=source_hash,
        **body.model_dump(),
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return {"id": field.id, "field_key": field.field_key}
