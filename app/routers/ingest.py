from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_user, get_current_admin

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/weather", response_model=schemas.Weather)
def ingest_weather_data(
    weather: schemas.WeatherCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_admin),
):
    """気象データを登録・更新します（管理者専用）。"""
    return crud.upsert_weather(db=db, weather=weather)


@router.post("/health_metrics", response_model=schemas.IngestResponseSummary)
def ingest_health_metrics_data(
    payload: schemas.HealthAutoExportPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Ingest a JSON payload from Health Auto Export.
    Parses and normalizes sleep, steps, and heart rate into structured tables.
    """
    summary = crud.process_and_save_health_metrics(
        db=db, payload=payload, user_id=current_user.id
    )
    db.commit()
    return summary


@router.post("/daily_state", response_model=schemas.DailyState)
def ingest_daily_state_data(
    daily_state: schemas.DailyStateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.upsert_daily_state(db=db, daily_state=daily_state, user_id=current_user.id)
