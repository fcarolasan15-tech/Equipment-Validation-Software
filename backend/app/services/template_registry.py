import hashlib
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.template import TemplateVersion, TemplateFile, TemplateStatusEnum
from app.config import settings


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def register_template_file(
    db: Session,
    template_version_id: int,
    source_path: Path,
    filename: str,
) -> TemplateFile:
    file_hash = compute_sha256(source_path)

    existing = db.query(TemplateFile).filter_by(sha256_hash=file_hash).first()
    if existing:
        return existing

    file_type = source_path.suffix.lstrip(".").lower()
    vault_dir = settings.vault_root / f"tv_{template_version_id}"
    vault_dir.mkdir(parents=True, exist_ok=True)
    vault_path = vault_dir / filename
    shutil.copy2(source_path, vault_path)

    tf = TemplateFile(
        template_version_id=template_version_id,
        filename=filename,
        file_type=file_type,
        vault_path=str(vault_path),
        sha256_hash=file_hash,
        file_size=source_path.stat().st_size,
    )
    db.add(tf)
    db.flush()
    return tf


def get_approved_template(db: Session, form_code: str) -> TemplateVersion | None:
    return (
        db.query(TemplateVersion)
        .filter_by(form_code=form_code, status=TemplateStatusEnum.APPROVED)
        .order_by(TemplateVersion.id.desc())
        .first()
    )
