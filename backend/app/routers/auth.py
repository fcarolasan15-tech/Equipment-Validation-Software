from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth import authenticate_user, create_access_token, hash_password, verify_password
from app.services.audit_logger import log_event
from app.schemas.auth import TokenResponse, ChangePasswordRequest, UserOut
from app.routers.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    user.last_login = datetime.now(timezone.utc)
    log_event(db, "USER_LOGIN", user_id=user.id,
               entity_type="User", entity_id=user.id,
               ip_address=request.client.host if request.client else None)
    db.commit()

    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, must_change_password=user.must_change_password)


@router.post("/change-password")
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    current_user.must_change_password = False
    log_event(db, "PASSWORD_CHANGED", user_id=current_user.id,
               entity_type="User", entity_id=current_user.id,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    roles = [ur.role.name.value for ur in current_user.user_roles]
    out = UserOut.model_validate(current_user)
    out.roles = roles
    return out
