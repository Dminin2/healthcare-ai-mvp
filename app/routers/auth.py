from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_db, get_current_user
from ..core.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


@router.post("/signup", response_model=schemas.UserRead, status_code=201,
             summary="ユーザー登録")
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """email と password で新規ユーザーを登録します。パスワードは bcrypt でハッシュ化されます。"""
    if _get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています。",
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
             summary="ログイン（JWT 取得）")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    email（username フィールドに入力）と password でログインし、
    Bearer JWT access token を返します。
    """
    user = _get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/setup", response_model=schemas.UserRead, status_code=201,
             summary="初回管理者ユーザー作成（admin が存在しない場合のみ）")
def setup_first_admin(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """DB に admin ユーザーが 0 人のときだけ実行できます。2 人目以降は 403。"""
    if db.query(models.User).filter(models.User.is_admin == True).first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者ユーザーは既に存在します。",
        )
    if _get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています。",
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
            summary="認証中ユーザー情報を取得")
def get_me(current_user: models.User = Depends(get_current_user)):
    """JWT から現在の認証ユーザー情報を返します。"""
    return current_user
