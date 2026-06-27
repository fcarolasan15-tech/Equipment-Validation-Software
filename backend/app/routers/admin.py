from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.database import get_db
from app.routers.deps import require_admin, get_current_user
from app.models.user import User, Role, UserRole, RoleEnum
from app.models.organization import Organization, Site
from app.services.auth import hash_password
from app.services.audit_logger import log_event

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    department: Optional[str] = None
    department_code: Optional[str] = None
    position: Optional[str] = None
    site_id: Optional[int] = None
    roles: list[str] = ["READ_ONLY"]


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    department_code: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[list[str]] = None


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).all()
    result = []
    for u in users:
        roles = [ur.role.name.value for ur in u.user_roles]
        result.append({
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "department": u.department, "department_code": u.department_code,
            "position": u.position, "is_active": u.is_active,
            "must_change_password": u.must_change_password, "roles": roles,
        })
    return result


@router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    existing = db.query(User).filter_by(email=body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        department=body.department,
        department_code=body.department_code,
        position=body.position,
        site_id=body.site_id,
        must_change_password=True,
    )
    db.add(user)
    db.flush()

    for role_name in body.roles:
        try:
            role_enum = RoleEnum(role_name)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown role: {role_name}")
        role = db.query(Role).filter_by(name=role_enum).first()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id))

    log_event(db, "USER_CREATED", user_id=admin.id, entity_type="User", entity_id=user.id,
               description=f"Created user {body.email}")
    db.commit()
    return {"id": user.id, "email": user.email, "message": "User created"}


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.department is not None:
        user.department = body.department
    if body.department_code is not None:
        user.department_code = body.department_code
    if body.position is not None:
        user.position = body.position
    if body.is_active is not None:
        user.is_active = body.is_active

    if body.roles is not None:
        db.query(UserRole).filter_by(user_id=user.id).delete()
        for role_name in body.roles:
            role = db.query(Role).filter_by(name=RoleEnum(role_name)).first()
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id))

    log_event(db, "USER_UPDATED", user_id=admin.id, entity_type="User", entity_id=user.id)
    db.commit()
    return {"message": "Updated"}


@router.get("/departments")
def list_departments(_: User = Depends(get_current_user)):
    return [
        {"department": "Pineapple Preparation Department", "section": "Receiving", "code": "RCV"},
        {"department": "Pineapple Preparation Department", "section": "Packing Table", "code": "PCT"},
        {"department": "Solids Processing Department", "section": "Cook Room", "code": "SPC"},
        {"department": "Solids Processing Department", "section": "Crush", "code": "SPR"},
        {"department": "Tropical Products Department", "section": "", "code": "TPD"},
        {"department": "Juice and Drinks", "section": "", "code": "JND"},
        {"department": "Liquids Processing Department", "section": "", "code": "LPD"},
        {"department": "Tetra and Flexible Packaging Department", "section": "Flexible Packaging", "code": "FPD"},
        {"department": "Tetra and Flexible Packaging Department", "section": "Tetra", "code": "TET"},
        {"department": "Packaging Operations Department", "section": "", "code": "POD"},
        {"department": "Brite Warehouse Department", "section": "", "code": "BWD"},
        {"department": "Can Plant Department", "section": "", "code": "CPD"},
        {"department": "Utilities Department", "section": "RACCA / Instrumentation", "code": "MIR"},
        {"department": "Utilities Department", "section": "Powerplant", "code": "MPP"},
        {"department": "Research and Development Department", "section": "Fruits, Beverage, Packaging", "code": "RND"},
        {"department": "Corporate Quality Management", "section": "Food Safety, Quality and Regulatory", "code": "FSR"},
        {"department": "Corporate Quality Management", "section": "Manufacturing QA", "code": "MQA"},
    ]
