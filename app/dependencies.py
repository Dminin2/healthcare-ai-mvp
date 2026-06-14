from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import SessionLocal
from . import models
from .core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    """Yields a database session; closed automatically after the request."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Decodes the Bearer JWT and returns the authenticated User model."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です。",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == uid).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise credentials_exception
    return user


def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Requires the authenticated user to be an admin (is_admin=True)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です。",
        )
    return current_user
