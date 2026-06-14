from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_current_user, get_current_admin

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/weather", response_model=schemas.Weather,
             summary="Ingest weather data (admin only)")
def ingest_weather_data(
    weather: schemas.WeatherCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_admin),
):
    """
    Create or update the weather record for the given date. Shared reference data —
    not scoped to any individual user. Requires admin privileges.
    """
    return crud.upsert_weather(db=db, weather=weather)


@router.post("/health_metrics", response_model=schemas.IngestResponseSummary,
             summary="Ingest health metrics from Health Auto Export")
def ingest_health_metrics_data(
    payload: schemas.HealthAutoExportPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Accept a JSON payload exported by the Health Auto Export app.
    Parses and stores sleep sessions, step counts, and resting heart rate
    into their respective tables, scoped to the authenticated user.
    """
    summary = crud.process_and_save_health_metrics(
        db=db, payload=payload, user_id=current_user.id
    )
    db.commit()
    return summary


@router.post("/daily_state", response_model=schemas.DailyState,
             summary="Submit a daily health state entry")
def ingest_daily_state_data(
    daily_state: schemas.DailyStateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create or update the daily mood, symptoms, and notes for the authenticated user
    on the specified date.
    """
    return crud.upsert_daily_state(db=db, daily_state=daily_state, user_id=current_user.id)
