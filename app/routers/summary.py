from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/summary", tags=["Summary"])


@router.get("/last7d", response_model=List[schemas.SummaryData],
            summary="Get a 7-day health and weather summary")
def get_last_7_days_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return one entry per day for the past 7 days, each combining weather conditions,
    daily state (mood, symptoms), and aggregated health metrics (steps, sleep, heart rate)
    for the authenticated user. Fields are `null` when no data exists for that day.
    """
    return crud.get_summary_last_n_days(db=db, user_id=current_user.id, days=7)
