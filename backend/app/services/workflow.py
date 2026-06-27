from sqlalchemy.orm import Session
from app.models.project import ProjectStageEnum, ValidationProject
from app.models.record import ValidationRecord, RecordStatusEnum, RecordStageEnum
from app.models.execution import Deviation, DeviationStatusEnum, DeviationSeverityEnum


STAGE_ORDER = [
    ProjectStageEnum.INITIATION,
    ProjectStageEnum.DQ,
    ProjectStageEnum.PROTOCOL,
    ProjectStageEnum.IQ,
    ProjectStageEnum.OQ,
    ProjectStageEnum.PQ,
    ProjectStageEnum.REPORT,
    ProjectStageEnum.RELEASED,
]

STAGE_TO_RECORD_STAGE = {
    ProjectStageEnum.DQ: RecordStageEnum.DQ,
    ProjectStageEnum.PROTOCOL: RecordStageEnum.PROTOCOL,
    ProjectStageEnum.IQ: RecordStageEnum.IQ,
    ProjectStageEnum.OQ: RecordStageEnum.OQ,
    ProjectStageEnum.PQ: RecordStageEnum.PQ,
    ProjectStageEnum.REPORT: RecordStageEnum.REPORT,
}


class WorkflowError(Exception):
    pass


def can_advance_to(db: Session, project: ValidationProject, target_stage: ProjectStageEnum) -> tuple[bool, str]:
    current_idx = STAGE_ORDER.index(project.current_stage)
    target_idx = STAGE_ORDER.index(target_stage)

    if target_idx != current_idx + 1:
        return False, f"Cannot skip stages. Current: {project.current_stage}, target: {target_stage}"

    if target_stage == ProjectStageEnum.DQ:
        return True, ""

    prior_stage = STAGE_ORDER[current_idx]
    record_stage = STAGE_TO_RECORD_STAGE.get(prior_stage)
    if not record_stage:
        return True, ""

    record = (
        db.query(ValidationRecord)
        .filter_by(project_id=project.id, stage=record_stage)
        .first()
    )
    if not record:
        return False, f"No record found for stage {prior_stage.value}"
    if record.status != RecordStatusEnum.APPROVED:
        return False, f"Record for stage {prior_stage.value} must be APPROVED before advancing"

    if target_stage == ProjectStageEnum.PQ:
        oq_record = (
            db.query(ValidationRecord)
            .filter_by(project_id=project.id, stage=RecordStageEnum.OQ)
            .first()
        )
        if oq_record:
            open_blocking = (
                db.query(Deviation)
                .filter(
                    Deviation.record_id == oq_record.id,
                    Deviation.status != DeviationStatusEnum.CLOSED,
                    Deviation.severity.in_([DeviationSeverityEnum.CRITICAL, DeviationSeverityEnum.MAJOR]),
                )
                .count()
            )
            if open_blocking > 0:
                return False, f"Cannot advance to PQ: {open_blocking} open CRITICAL/MAJOR deviation(s) in OQ"

    return True, ""


def advance_stage(db: Session, project: ValidationProject, target_stage: ProjectStageEnum) -> ValidationProject:
    ok, reason = can_advance_to(db, project, target_stage)
    if not ok:
        raise WorkflowError(reason)
    project.current_stage = target_stage
    db.flush()
    return project


def get_recommended_scope(risk_level: str, urs_impact: str) -> dict:
    matrix = {
        ("DIRECT", "HIGH"):   {"iq": "REQUIRED", "oq": "REQUIRED", "pq": "REQUIRED"},
        ("DIRECT", "MEDIUM"): {"iq": "REQUIRED", "oq": "REQUIRED", "pq": "OPTIONAL"},
        ("DIRECT", "LOW"):    {"iq": "REQUIRED", "oq": "OPTIONAL", "pq": "NOT_REQUIRED"},
        ("INDIRECT", "HIGH"):   {"iq": "REQUIRED", "oq": "REQUIRED", "pq": "OPTIONAL"},
        ("INDIRECT", "MEDIUM"): {"iq": "REQUIRED", "oq": "OPTIONAL", "pq": "NOT_REQUIRED"},
        ("INDIRECT", "LOW"):    {"iq": "OPTIONAL", "oq": "NOT_REQUIRED", "pq": "NOT_REQUIRED"},
        ("SAFETY", "HIGH"):   {"iq": "REQUIRED", "oq": "OPTIONAL", "pq": "NOT_REQUIRED"},
        ("SAFETY", "MEDIUM"): {"iq": "OPTIONAL", "oq": "NOT_REQUIRED", "pq": "NOT_REQUIRED"},
        ("SAFETY", "LOW"):    {"iq": "NOT_REQUIRED", "oq": "NOT_REQUIRED", "pq": "NOT_REQUIRED"},
        ("NONE", "HIGH"):   {"iq": "NOT_REQUIRED", "oq": "NOT_REQUIRED", "pq": "NOT_REQUIRED"},
        ("NONE", "MEDIUM"): {"iq": "NOT_REQUIRED", "oq": "NOT_REQUIRED", "pq": "NOT_REQUIRED"},
        ("NONE", "LOW"):    {"iq": "NOT_REQUIRED", "oq": "NOT_REQUIRED", "pq": "NOT_REQUIRED"},
    }
    return matrix.get((urs_impact, risk_level), {"iq": "REQUIRED", "oq": "REQUIRED", "pq": "REQUIRED"})
