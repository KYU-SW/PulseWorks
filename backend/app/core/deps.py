from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User


def get_current_user(
    authorization: str = Header(...), db: Session = Depends(get_db)
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter_by(id=int(payload["sub"])).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles):
    """Dependency factory: which API a role may call. This is the single
    place role checks live — routers must depend on this rather than
    hardcoding role comparisons per endpoint. It answers "can this role
    use this API at all", which is a different question from
    `can_access_patient` ("can this specific user touch this specific
    patient's data")."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden for this role")
        return user

    return _checker
