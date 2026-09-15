from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.audit import write_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email).first()
    # Same generic error, same status code, whether the email doesn't exist
    # at all or the password is wrong — never reveal which one it was.
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), role=user.role.value)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action="LOGIN",
        resource_type="Auth",
        resource_id=str(user.id),
        reason="login_success",
        patient_id=user.patient_id,
    )
    db.commit()

    return TokenResponse(access_token=token)
