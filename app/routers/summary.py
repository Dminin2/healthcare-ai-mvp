from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/summary", tags=["Summary"])


@router.get("/last7d", response_model=List[schemas.SummaryData])
def get_last_7_days_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns a 7-day summary integrating weather, daily state, and health metrics."""
    return crud.get_summary_last_n_days(db=db, user_id=current_user.id, days=7)
