from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, db

router = APIRouter()

# Dependency to get the DB session
def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

@router.get("/last7d", response_model=List[schemas.SummaryData])
def get_last_7_days_summary(db: Session = Depends(get_db)):
    """
    Returns a summary of the last 7 days, with one entry per day.
    """
    return crud.get_summary_last_n_days(db=db, days=7)
