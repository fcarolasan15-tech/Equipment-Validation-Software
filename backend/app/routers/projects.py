from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.models.project import ValidationProject, ProjectStageEnum
from app.schemas.project import ProjectCreate, ProjectOut, StageAdvanceRequest
from app.services.audit_logger import log_event
from app.services.workflow import advance_stage, WorkflowError, can_advance_to

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _gen_project_number(db: Session) -> str:
    count = db.query(ValidationProject).count() + 1
    return f"VP-{datetime.now(timezone.utc).year}-{count:04d}"


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ValidationProject).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = ValidationProject(
        **body.model_dump(),
        owner_id=user.id,
        project_number=_gen_project_number(db),
    )
    db.add(project)
    log_event(db, "PROJECT_CREATED", user_id=user.id, entity_type="ValidationProject",
               description=body.title)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.query(ValidationProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.post("/{project_id}/advance-stage")
def advance_project_stage(
    project_id: int,
    body: StageAdvanceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(ValidationProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    try:
        target = ProjectStageEnum(body.target_stage)
        advance_stage(db, project, target)
        log_event(db, "STAGE_ADVANCED", user_id=user.id, entity_type="ValidationProject",
                   entity_id=project_id, new_values={"stage": target.value})
        db.commit()
    except WorkflowError as e:
        raise HTTPException(400, str(e))
    return {"current_stage": project.current_stage}


@router.get("/{project_id}/stage-gates")
def stage_gates(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.query(ValidationProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    gates = []
    from app.services.workflow import STAGE_ORDER
    idx = STAGE_ORDER.index(project.current_stage)
    if idx + 1 < len(STAGE_ORDER):
        next_stage = STAGE_ORDER[idx + 1]
        ok, reason = can_advance_to(db, project, next_stage)
        gates.append({"next_stage": next_stage.value, "can_advance": ok, "reason": reason})
    return gates
