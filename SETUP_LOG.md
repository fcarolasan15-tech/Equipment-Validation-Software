# DMPI Equipment Validation Software — Setup & Issue Log

**Project:** Kneat-Like Equipment Validation Software  
**Client:** Del Monte Philippines Inc. (DMPI)  
**Branch:** `claude/equipment-validation-software-2xbs87`  
**Repository:** https://github.com/fcarolasan15-tech/equipment-validation-software  
**Date:** June 27, 2026  

---

## What Was Built

A full-stack regulated validation document management system covering the complete **DQ → Protocol → IQ → OQ → PQ → Report → Released** lifecycle, modeled after the DMPI Site Validation Program (SYP-FSR-01) and blank templates F-FSR-01 through F-FSR-06.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ (tested), FastAPI |
| Database | SQLite (dev) via SQLAlchemy 2 + Alembic migrations |
| DOCX fill | python-docx (`{{placeholder}}` replacement + ☒/☐ checkboxes) |
| XLSX fill | openpyxl (named ranges + placeholder scan) |
| PDF render | LibreOffice headless (`soffice --headless --convert-to pdf`) |
| PDF visual diff | Pillow + pdf2image *(optional — see issues below)* |
| Auth | PyJWT + bcrypt (password-verified electronic signatures) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Container | Docker + nginx |

---

## Files Delivered

```
Equipment-Validation-Software/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory + CORS
│   │   ├── config.py                # Settings (vault paths, JWT, LibreOffice bin)
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   ├── models/                  # 15-table ORM schema
│   │   │   ├── organization.py      # organizations, sites
│   │   │   ├── user.py              # users, roles, user_roles
│   │   │   ├── asset.py             # assets + 8-metric risk scoring
│   │   │   ├── template.py          # template_versions, files, field_maps
│   │   │   ├── project.py           # validation_projects
│   │   │   ├── record.py            # validation_records, record_versions
│   │   │   ├── execution.py         # execution_items, deviations
│   │   │   ├── signature.py         # e-signatures
│   │   │   └── audit.py             # audit_events, render_jobs, attachments
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── routers/                 # API route handlers
│   │   │   ├── auth.py              # login, change-password, /me
│   │   │   ├── admin.py             # user management, department lookup
│   │   │   ├── assets.py            # asset CRUD + risk assessment
│   │   │   ├── projects.py          # project CRUD + stage advance
│   │   │   ├── records.py           # full record lifecycle + deviations + PDF
│   │   │   └── templates.py         # template version management
│   │   ├── services/
│   │   │   ├── auth.py              # bcrypt hash/verify, JWT encode/decode
│   │   │   ├── audit_logger.py      # immutable audit event writer
│   │   │   ├── docx_filler.py       # clone DOCX + fill {{placeholders}}
│   │   │   ├── xlsx_filler.py       # clone XLSX + fill named ranges
│   │   │   ├── render_worker.py     # LibreOffice headless PDF conversion
│   │   │   ├── visual_diff.py       # pixel-level PDF comparison (optional)
│   │   │   ├── workflow.py          # stage gate logic + scope matrix
│   │   │   └── template_registry.py # SHA-256 hash + vault copy
│   │   └── seed/seed.py             # seeds org, site, users, sample asset
│   ├── migrations/                  # Alembic (1 initial migration)
│   ├── tests/                       # 15 passing unit tests
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # React Router with auth guard
│   │   ├── api/                     # typed axios wrappers (auth, assets, projects, records)
│   │   ├── components/
│   │   │   ├── Layout.tsx           # header with DMPI logo + nav
│   │   │   ├── Badge.tsx            # colour-coded status chips
│   │   │   └── StagePipeline.tsx    # visual stage progress bar
│   │   └── pages/
│   │       ├── Login.tsx            # login with DMPI logo
│   │       ├── ChangePassword.tsx   # forced on first login
│   │       ├── Dashboard.tsx        # KPI cards + active projects table
│   │       ├── AssetList.tsx        # asset register table
│   │       ├── AssetNew.tsx         # register asset + dept dropdown
│   │       ├── AssetDetail.tsx      # 8-metric risk form + recommended scope
│   │       ├── ProjectList.tsx      # all projects table
│   │       ├── ProjectNew.tsx       # new project wizard + auto scope
│   │       ├── ProjectWorkspace.tsx # stage pipeline + record links
│   │       ├── RecordEditor.tsx     # data entry, approve, deviations, audit, PDF
│   │       ├── TemplateLibrary.tsx  # upload + approve F-FSR-01 to -06
│   │       └── ApprovalQueue.tsx    # all IN_REVIEW records
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── .gitignore                       # excludes templates/, storage/, *.docx, *.pdf
└── README.md
```

---

## Key Features

### Workflow Stage Gates
- Stages: `INITIATION → DQ → PROTOCOL → IQ → OQ → PQ → REPORT → RELEASED`
- Each advance requires the prior stage record to be **APPROVED**
- Advancing to **PQ is blocked** if open CRITICAL or MAJOR deviations exist in OQ

### Risk Assessment (Annex II of SYP-FSR-01)
- 8 metrics scored 1 (conforming) or 2 (non-conforming)
- Risk Score = product of all 8 (range: 1–256)
- LOW: 1–4 | MEDIUM: 8–16 | HIGH: ≥32
- Auto-suggests IQ/OQ/PQ scope from Annex III matrix (URS Impact × Risk Level)

### Electronic Signatures
- Approval requires password re-entry — stored as `Signature` record
- All state changes logged to immutable `audit_events` table

### Template Filling
- DOCX: clones master file, replaces `{{field_key}}` in paragraphs, table cells, headers/footers
- XLSX: clones master file, fills named ranges first, falls back to `{{field_key}}` cell scan
- PDF: generated via LibreOffice headless (not HTML/CSS)

### Seeded Data
- Organization: Del Monte Philippines Inc.
- Site: Bugo Plant
- 17 department codes (Annex IV)
- Admin user: `admin@dmpi.com.ph`
- Validation Engineer: `ve@dmpi.com.ph`
- Sample asset: EQ-BGP-001

---

## Test Results

```
15 passed, 1 warning
```

| Test File | Tests | Result |
|---|---|---|
| test_workflow_gates.py | 8 | PASS |
| test_audit_trail.py | 3 | PASS |
| test_docx_filler.py | 3 | PASS |
| test_xlsx_filler.py | 1 | PASS |

---

## Errors Encountered and Fixes Applied

### Error 1 — bcrypt version mismatch
**When:** First run of `python -m app.seed.seed`  
**Error:**
```
AttributeError: module 'bcrypt' has no attribute '__about__'
ValueError: password cannot be longer than 72 bytes
```
**Cause:** `passlib 1.7.4` (abandoned since 2020) was incompatible with modern `bcrypt` versions. It tried to read `bcrypt.__about__.__version__` which no longer exists.  
**Fix:** Replaced `passlib` entirely with direct `bcrypt` calls. Replaced `python-jose` with `PyJWT 2.8.0`.

---

### Error 2 — `crypt` module removed in Python 3.13+
**When:** Running on Python 3.13 or 3.14  
**Error:**
```
ModuleNotFoundError: No module named 'crypt'
```
**Cause:** Python 3.13 removed the `crypt` standard library module that `passlib` depended on as a fallback.  
**Fix:** Same as Error 1 — passlib removed entirely.

---

### Error 3 — Pillow 10.3.0 fails to build on Python 3.14 (Windows)
**When:** `pip install -r requirements.txt` on Python 3.14 Windows  
**Error:**
```
ERROR: Failed to build 'Pillow' when getting requirements to build wheel
KeyError: '__version__'
```
**Cause:** `Pillow 10.3.0` predates Python 3.14 and has no pre-built wheel for `cp314-win_amd64`. Building from source failed.  
**Fix:** Removed `Pillow` and `pdf2image` from core `requirements.txt`. Moved to optional commented-out section. `visual_diff.py` already handles `ImportError` gracefully (returns `-1.0`). The core app (template filling, PDF generation, web UI) does not need Pillow.

---

### Error 4 — pydantic-core 2.18.2 fails Rust compilation on Python 3.14 (Windows)
**When:** `pip install -r requirements.txt` on Python 3.14 Windows  
**Error:**
```
Downloading pydantic_core-2.18.2.tar.gz (383 kB)
Getting requirements to build wheel ... done
Installing backend dependencies ... done
Preparing metadata (pyproject.toml) ... [hangs / fails]
```
**Cause:** `pydantic 2.7.1` depends on `pydantic-core 2.18.2` which has no `cp314` wheel. pip falls back to compiling from Rust source, which requires the Rust toolchain and often fails.  
**Fix:** Changed all version pins from `==` (exact) to `>=` (minimum). `pydantic>=2.10.0` ships `cp314-win_amd64` wheels. pip now downloads a pre-built wheel instead of compiling.

---

### Error 5 — `alembic` not found on PATH (Windows)
**When:** Running `alembic upgrade head` in PowerShell  
**Error:**
```
alembic : The term 'alembic' is not recognized as the name of a cmdlet...
```
**Cause:** On Windows, pip-installed script entry points are sometimes not added to `PATH` automatically depending on the Python installation method.  
**Fix:** Use `python -m alembic upgrade head` instead of bare `alembic`. Same applies to `uvicorn` → `python -m uvicorn`.

---

## Correct Setup Commands (Windows PowerShell, Python 3.14)

```powershell
# 1. Clone and checkout
git clone https://github.com/fcarolasan15-tech/equipment-validation-software.git
cd equipment-validation-software
git checkout claude/equipment-validation-software-2xbs87

# 2. Backend setup (run in: equipment-validation-software\backend)
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seed.seed

# 3. Start backend (keep this window open)
python -m uvicorn app.main:app --port 8000

# 4. Open a second PowerShell window — Frontend setup
cd equipment-validation-software\frontend
npm install
npm run dev
```

Open browser: **http://localhost:5173**

| Account | Email | Password |
|---|---|---|
| Admin | admin@dmpi.com.ph | changeme123 |
| Engineer | ve@dmpi.com.ph | changeme123 |

> First login forces a mandatory password change.

---

## Known Limitations / Pending

| Item | Status | Notes |
|---|---|---|
| PDF generation | Requires LibreOffice installed on Windows | Download free from libreoffice.org |
| PDF visual diff | Not available without Pillow + pdf2image | Optional feature only |
| PostgreSQL support | Config ready (`DATABASE_URL` env var) | Currently runs SQLite |
| F-FSR-01 to -06 templates | Must be uploaded manually via Template Library | Admin → Templates → Upload |
| SMTP / email notifications | Not implemented | Future enhancement |

---

## LibreOffice (for PDF Generation)

PDF generation requires LibreOffice. Install it free:

1. Go to **https://www.libreoffice.org/download**
2. Download and install the Windows version
3. After install, `soffice` should be available in your PATH
4. The app will automatically use it when you click **Generate PDF** in any record

---

*Generated by Claude Code — DMPI Equipment Validation Software project session, June 27, 2026*
