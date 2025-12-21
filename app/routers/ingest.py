from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Any
from .. import crud, schemas
from ..dependencies import get_db

router = APIRouter(
    prefix="/ingest",
    tags=["Ingestion"]
)

@router.post("/weather", response_model=schemas.Weather)
def ingest_weather_data(weather: schemas.WeatherCreate, db: Session = Depends(get_db)):
    return crud.upsert_weather(db=db, weather=weather)

import os

@router.post(
    "/health_metrics",
    response_model=schemas.IngestResponseSummary
)
def ingest_health_metrics_data(
    payload: schemas.HealthAutoExportPayload,
    db: Session = Depends(get_db)
):
    """
    Ingest a JSON payload from Health Auto Export.
    This endpoint parses the complex payload, saves the raw data,
    and normalizes known metrics (sleep, steps, heart rate) into
    structured database tables.
    """
    summary = crud.process_and_save_health_metrics(db=db, payload=payload)
    if os.getenv("TESTING") != "True": # Only commit if not in test environment
        db.commit()
    return summary

@router.post("/daily_state", response_model=schemas.DailyState)
def ingest_daily_state_data(daily_state: schemas.DailyStateCreate, db: Session = Depends(get_db)):
    return crud.upsert_daily_state(db=db, daily_state=daily_state)