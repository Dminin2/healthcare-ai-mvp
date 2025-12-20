from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import crud, schemas, db

router = APIRouter()

# Dependency to get the DB session
def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

@router.get(
    "/latest",
    response_model=schemas.LatestHealthSummary,
    tags=["Health Summary"]
)
def get_latest_health_summary(db: Session = Depends(get_db)):
    """
    Returns a summary of the latest available health data, including:
    - The most recent sleep session.
    - The most recent resting heart rate.
    - The total step count for the current day (UTC).
    """
    return crud.get_latest_health_summary(db=db)
