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

@router.post("/weather", response_model=schemas.Weather)
def ingest_weather_data(weather: schemas.WeatherCreate, db: Session = Depends(get_db)):
    return crud.upsert_weather(db=db, weather=weather)

@router.post("/health_metrics", response_model=schemas.HealthMetrics)
def ingest_health_metrics_data(health_metrics: schemas.HealthMetricsCreate, db: Session = Depends(get_db)):
    return crud.upsert_health_metrics(db=db, health_metrics=health_metrics)

@router.post("/daily_state", response_model=schemas.DailyState)
def ingest_daily_state_data(daily_state: schemas.DailyStateCreate, db: Session = Depends(get_db)):
    return crud.upsert_daily_state(db=db, daily_state=daily_state)
