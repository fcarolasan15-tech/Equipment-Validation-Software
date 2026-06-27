# DMPI Equipment Validation Software

Regulated validation document management system for Del Monte Philippines Inc. — manages the full DQ→Protocol→IQ→OQ→PQ→Report lifecycle using controlled DOCX/XLSX master templates (F-FSR-01 to F-FSR-06).

## Quick Start (Development)

### Backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m app.seed.seed          # creates admin + sample data
uvicorn app.main:app --reload    # http://localhost:8000/docs
```

**Default credentials** (change on first login):
- Admin: `admin@dmpi.com.ph` / `changeme123`
- Validation Engineer: `ve@dmpi.com.ph` / `changeme123`

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

### Docker (Production)

```bash
docker compose up --build
```

Frontend → `http://localhost:80`  
Backend API docs → `http://localhost:8000/docs`

---

## Architecture

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | SQLite (dev) / PostgreSQL-compatible via SQLAlchemy 2 |
| Migrations | Alembic |
| DOCX fill | python-docx (`{{field_key}}` placeholder replacement) |
| XLSX fill | openpyxl (named ranges + placeholder scan) |
| PDF render | LibreOffice headless (`soffice --headless --convert-to pdf`) |
| Visual diff | pdf2image + Pillow pixel comparison |
| Auth | JWT (python-jose) + bcrypt, password-verified e-signatures |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |

## Workflow Stages

`INITIATION → DQ → PROTOCOL → IQ → OQ → PQ → REPORT → RELEASED`

Each stage transition requires the prior stage record to be **APPROVED**. Advancing to PQ is blocked if open CRITICAL/MAJOR deviations exist in OQ.

## Risk Assessment

8-metric multiplicative scoring (1=conforming, 2=non-conforming):
- Score range: 1–256 | LOW: 1–4 | MEDIUM: 8–16 | HIGH: ≥32
- Auto-suggests IQ/OQ/PQ scope from Annex III matrix (URS Impact × Risk Level)

## Templates (F-FSR-01 to F-FSR-06)

Upload master DOCX/XLSX files via the Template Library (admin only). Each template version is SHA-256 hashed. Approve a version to make it available for new records. Field maps link `{{placeholder}}` keys to form fields.

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Security Notes

- `templates/` and `storage/` directories are git-ignored — never commit master templates or generated records
- Electronic signatures require password re-entry and are logged in the immutable audit trail
- All state changes produce `audit_events` records with user, timestamp, and old/new values
