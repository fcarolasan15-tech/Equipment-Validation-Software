import subprocess
import hashlib
import shutil
from pathlib import Path
from app.config import settings


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def render_to_pdf(source_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            settings.libreoffice_bin,
            "--headless",
            "--convert-to", "pdf:writer_pdf_Export",
            "--outdir", str(output_dir),
            str(source_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    pdf_path = output_dir / (source_path.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(f"Expected PDF not found at {pdf_path}")
    return pdf_path


def get_page_count(pdf_path: Path) -> int:
    try:
        from pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(pdf_path))
        return info.get("Pages", 0)
    except Exception:
        return 0
