import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_db, get_current_user
from ..core.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


@router.post("/signup", response_model=schemas.UserRead, status_code=201,
             summary="Register a new user")
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user account. Passwords are hashed with bcrypt before storage."""
    if _get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )
    user = models.User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token,
             summary="Log in and obtain a JWT access token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate with email (enter in the `username` field) and password.
    Returns a Bearer JWT access token to use in subsequent requests.
    """
    user = _get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/setup", response_model=schemas.UserRead, status_code=201,
             summary="Bootstrap the first admin user (one-time setup)")
def setup_first_admin(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    x_setup_secret: Optional[str] = Header(default=None),
):
    """
    Create the initial admin account. Requires a valid X-Setup-Secret header matching
    the SETUP_SECRET environment variable. Only succeeds when no admin user exists.
    Returns 403 if the secret is missing/invalid or an admin already exists.
    """
    _setup_secret = os.getenv("SETUP_SECRET")
    if not _setup_secret or x_setup_secret != _setup_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing setup secret.",
        )
    if db.query(models.User).filter(models.User.is_admin == True).first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An admin user already exists.",
        )
    if _get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )
    user = models.User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        created_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=schemas.UserRead,
            summary="Get the current authenticated user")
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return profile information for the user identified by the Bearer token."""
    return current_user
