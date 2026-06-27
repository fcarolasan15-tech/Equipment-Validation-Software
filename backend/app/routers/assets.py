from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetOut, RiskAssessmentUpdate
from app.services.audit_logger import log_event
from app.services.workflow import get_recommended_scope

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
def list_assets(site_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = db.query(Asset)
    if site_id:
        q = q.filter_by(site_id=site_id)
    return q.all()


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(body: AssetCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = Asset(**body.model_dump())
    asset.compute_risk()
    db.add(asset)
    log_event(db, "ASSET_CREATED", user_id=user.id, entity_type="Asset", description=body.equipment_name)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.put("/{asset_id}/risk-assessment", response_model=AssetOut)
def update_risk(asset_id: int, body: RiskAssessmentUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")

    old_score = asset.risk_score
    for field, value in body.model_dump(exclude_none=True).items():
        if hasattr(asset, field):
            setattr(asset, field, value)
    asset.compute_risk()

    log_event(db, "RISK_ASSESSMENT_UPDATED", user_id=user.id, entity_type="Asset", entity_id=asset_id,
               old_values={"risk_score": old_score}, new_values={"risk_score": asset.risk_score})
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{asset_id}/recommended-scope")
def recommended_scope(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if not asset.risk_level or not asset.urs_impact:
        return {"message": "Set risk assessment first", "scope": None}
    scope = get_recommended_scope(asset.risk_level.value, asset.urs_impact.value)
    return {
        "risk_score": asset.risk_score,
        "risk_level": asset.risk_level,
        "urs_impact": asset.urs_impact,
        "recommended_scope": scope,
    }
