import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.models.record import ValidationRecord, RecordVersion, RecordStatusEnum
from app.models.execution import ExecutionItem, Deviation, DeviationStatusEnum
from app.models.signature import Signature, SignatureRoleEnum
from app.models.audit import RenderJob, Attachment, RenderStatusEnum
from app.schemas.record import (RecordCreate, RecordDataUpdate, RecordOut,
                                 SignRequest, DeviationCreate, DeviationOut, ExecutionItemUpdate)
from app.services.audit_logger import log_event
from app.services.auth import verify_password
from app.config import settings

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
def list_records(project_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = db.query(ValidationRecord)
    if project_id:
        q = q.filter_by(project_id=project_id)
    return q.all()


@router.post("", response_model=RecordOut, status_code=201)
def create_record(body: RecordCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = ValidationRecord(**body.model_dump(), prepared_by_id=user.id,
                               prepared_at=datetime.now(timezone.utc))
    db.add(record)
    log_event(db, "RECORD_CREATED", user_id=user.id, entity_type="ValidationRecord",
               description=f"Stage: {body.stage}")
    db.commit()
    db.refresh(record)
    return record


@router.get("/{record_id}", response_model=RecordOut)
def get_record(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    return record


@router.put("/{record_id}/data")
def update_record_data(record_id: int, body: RecordDataUpdate,
                        db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    if record.status == RecordStatusEnum.APPROVED:
        raise HTTPException(400, "Cannot edit an approved record")

    version_count = db.query(RecordVersion).filter_by(record_id=record_id).count()
    snap = RecordVersion(
        record_id=record_id,
        version_number=version_count + 1,
        field_data_snapshot=record.field_data,
        changed_by_id=user.id,
        change_reason=body.change_reason,
    )
    db.add(snap)
    record.field_data = body.field_data
    log_event(db, "RECORD_DATA_UPDATED", user_id=user.id, entity_type="ValidationRecord", entity_id=record_id)
    db.commit()
    return {"message": "Saved", "version": version_count + 1}


@router.post("/{record_id}/submit-review")
def submit_for_review(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    if record.status != RecordStatusEnum.DRAFT:
        raise HTTPException(400, "Record is not in DRAFT status")
    record.status = RecordStatusEnum.IN_REVIEW
    log_event(db, "RECORD_SUBMITTED_FOR_REVIEW", user_id=user.id, entity_type="ValidationRecord", entity_id=record_id)
    db.commit()
    return {"status": record.status}


@router.post("/{record_id}/approve")
def approve_record(record_id: int, body: SignRequest,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    if record.status != RecordStatusEnum.IN_REVIEW:
        raise HTTPException(400, "Record must be IN_REVIEW to approve")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(400, "Password verification failed — electronic signature requires password confirmation")

    record.status = RecordStatusEnum.APPROVED
    record.approved_by_id = user.id
    record.approved_at = datetime.now(timezone.utc)

    sig = Signature(
        record_id=record_id, user_id=user.id,
        role=SignatureRoleEnum.APPROVED_BY,
        meaning=body.meaning or "I approve this document",
        password_verified="Y",
    )
    db.add(sig)
    log_event(db, "RECORD_APPROVED", user_id=user.id, entity_type="ValidationRecord", entity_id=record_id)
    db.commit()
    return {"status": record.status, "approved_by": user.full_name, "approved_at": record.approved_at}


@router.post("/{record_id}/reject")
def reject_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    record.status = RecordStatusEnum.REJECTED
    log_event(db, "RECORD_REJECTED", user_id=user.id, entity_type="ValidationRecord", entity_id=record_id)
    db.commit()
    return {"status": record.status}


@router.post("/{record_id}/render-pdf")
def render_pdf(record_id: int, background_tasks: BackgroundTasks,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")

    job = RenderJob(record_id=record_id, triggered_by_id=user.id, status=RenderStatusEnum.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_do_render, job.id)
    return {"job_id": job.id, "status": "PENDING"}


def _do_render(job_id: int):
    from app.database import SessionLocal
    from app.services.render_worker import render_to_pdf, compute_sha256, get_page_count
    from app.services.docx_filler import fill_docx
    from app.services.xlsx_filler import fill_xlsx
    from app.models.template import TemplateFile

    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter_by(id=job_id).first()
        if not job:
            return
        job.status = RenderStatusEnum.RUNNING
        db.commit()

        record = db.query(ValidationRecord).filter_by(id=job.record_id).first()
        tf = db.query(TemplateFile).filter_by(template_version_id=record.template_version_id).first()
        if not tf:
            job.status = RenderStatusEnum.FAILED
            job.error_message = "No template file found"
            db.commit()
            return

        output_dir = Path(settings.storage_root) / f"project_{record.project_id}" / f"record_{record.id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        source = Path(tf.vault_path)

        if tf.file_type == "docx":
            filled = fill_docx(source, output_dir / f"filled_{source.name}", record.field_data or {})
        else:
            filled = fill_xlsx(source, output_dir / f"filled_{source.name}", record.field_data or {})

        pdf_path = render_to_pdf(filled, output_dir)
        pdf_hash = compute_sha256(pdf_path)
        page_count = get_page_count(pdf_path)

        job.status = RenderStatusEnum.COMPLETE
        job.source_file_path = str(filled)
        job.output_pdf_path = str(pdf_path)
        job.pdf_hash = pdf_hash
        job.page_count = page_count
        job.completed_at = datetime.now(timezone.utc)

        record.current_pdf_path = str(pdf_path)
        record.current_pdf_hash = pdf_hash
        db.commit()
    except Exception as e:
        try:
            job.status = RenderStatusEnum.FAILED
            job.error_message = str(e)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/{record_id}/render-status/{job_id}")
def render_status(record_id: int, job_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = db.query(RenderJob).filter_by(id=job_id, record_id=record_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return {"job_id": job.id, "status": job.status, "pdf_hash": job.pdf_hash,
            "page_count": job.page_count, "error": job.error_message}


@router.get("/{record_id}/download-pdf")
def download_pdf(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    if not record.current_pdf_path or not Path(record.current_pdf_path).exists():
        raise HTTPException(404, "PDF not yet generated")
    return FileResponse(record.current_pdf_path, media_type="application/pdf",
                        filename=f"record_{record_id}.pdf")


@router.get("/{record_id}/audit-trail")
def audit_trail(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from app.models.audit import AuditEvent
    events = db.query(AuditEvent).filter_by(entity_type="ValidationRecord", entity_id=record_id).all()
    return [{"id": e.id, "event_type": e.event_type, "description": e.description,
             "user_id": e.user_id, "created_at": e.created_at} for e in events]


@router.post("/{record_id}/attachments", status_code=201)
async def upload_attachment(record_id: int, file: UploadFile = File(...),
                             description: str = "",
                             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    import hashlib, aiofiles
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")

    att_dir = Path(settings.storage_root) / f"project_{record.project_id}" / f"record_{record_id}" / "attachments"
    att_dir.mkdir(parents=True, exist_ok=True)
    dest = att_dir / file.filename

    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    att = Attachment(
        record_id=record_id, uploaded_by_id=user.id,
        filename=file.filename, content_type=file.content_type,
        vault_path=str(dest), file_size=len(content), sha256_hash=sha256,
        description=description,
    )
    db.add(att)
    log_event(db, "ATTACHMENT_UPLOADED", user_id=user.id, entity_type="ValidationRecord", entity_id=record_id,
               description=file.filename)
    db.commit()
    return {"id": att.id, "filename": att.filename, "sha256": sha256}


@router.get("/{record_id}/attachments")
def list_attachments(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Attachment).filter_by(record_id=record_id).all()


# Execution items
@router.get("/{record_id}/execution-items")
def list_execution_items(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ExecutionItem).filter_by(record_id=record_id).all()


@router.put("/{record_id}/execution-items/{item_id}")
def update_execution_item(record_id: int, item_id: int, body: ExecutionItemUpdate,
                           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(ExecutionItem).filter_by(id=item_id, record_id=record_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    item.actual_result = body.actual_result
    item.status = body.status
    item.notes = body.notes
    item.executed_by_id = user.id
    item.executed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Updated"}


# Deviations
@router.post("/{record_id}/deviations", response_model=DeviationOut, status_code=201)
def create_deviation(record_id: int, body: DeviationCreate,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(ValidationRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")

    count = db.query(Deviation).filter_by(record_id=record_id).count()
    dev_number = f"DEV-{record_id:04d}-{count+1:03d}"
    dev = Deviation(
        **body.model_dump(),
        deviation_number=dev_number,
        raised_by_id=user.id,
    )
    db.add(dev)
    log_event(db, "DEVIATION_RAISED", user_id=user.id, entity_type="ValidationRecord", entity_id=record_id,
               description=dev_number)
    db.commit()
    db.refresh(dev)
    return dev


@router.get("/{record_id}/deviations", response_model=list[DeviationOut])
def list_deviations(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Deviation).filter_by(record_id=record_id).all()


@router.post("/{record_id}/deviations/{dev_id}/close")
def close_deviation(record_id: int, dev_id: int,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dev = db.query(Deviation).filter_by(id=dev_id, record_id=record_id).first()
    if not dev:
        raise HTTPException(404, "Deviation not found")
    dev.status = DeviationStatusEnum.CLOSED
    dev.closed_by_id = user.id
    dev.closed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "CLOSED"}
