from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime, timezone
import json
from typing import Dict, Any, List
from enum import Enum

from . import models, schemas
from dateutil.parser import parse as dateutil_parse

# --- NEW CRUD for Health Auto Export ---

def parse_and_save_metric(db: Session, metric: schemas.HealthMetric, summary: schemas.IngestResponseSummary):
    """Parses a single metric from the payload and saves it to the appropriate table."""
    metric_name = metric.name
    
    for item in metric.data:
        try:
            # Centralized date parsing
            record_time_str = item.get("date") or item.get("sleepStart")
            if not record_time_str:
                summary.warnings.append(f"Missing date identifier in item for '{metric_name}': {item}")
                summary.records_skipped += 1
                continue
            
            # Use the more lenient `parse` instead of `isoparse`
            record_time = dateutil_parse(record_time_str)

            if metric_name == "resting_heart_rate":
                value = schemas.to_float(item.get("qty"))
                if value is None:
                    summary.warnings.append(f"Could not parse 'qty' for resting_heart_rate at {record_time_str}")
                    summary.records_skipped += 1
                    continue
                
                db_record = models.RestingHeartRate(
                    timestamp=record_time,
                    value=int(value),
                    unit=metric.units,
                    source=item.get("source")
                )
                db.add(db_record)
                summary.records_inserted += 1

            elif metric_name == "step_count":
                value = schemas.to_float(item.get("qty"))
                if value is None:
                    summary.warnings.append(f"Could not parse 'qty' for step_count at {record_time_str}")
                    summary.records_skipped += 1
                    continue

                db_record = models.StepCount(
                    timestamp=record_time,
                    value=value,
                    unit=metric.units,
                    source=item.get("source")
                )
                db.add(db_record)
                summary.records_inserted += 1

            elif metric_name == "sleep_analysis":
                start_time = dateutil_parse(item["sleepStart"])
                end_time = dateutil_parse(item["sleepEnd"])
                
                db_record = models.SleepSession(
                    session_start_time=start_time,
                    session_end_time=end_time,
                    total_sleep_hours=schemas.to_float(item["totalSleep"]),
                    deep_hours=schemas.to_float(item.get("deep")),
                    rem_hours=schemas.to_float(item.get("rem")),
                    core_hours=schemas.to_float(item.get("core")),
                    awake_hours=schemas.to_float(item.get("awake")),
                    source=item.get("source"),
                    raw_date_str=item["date"],
                    created_at=datetime.now(timezone.utc)
                )
                db.add(db_record)
                summary.records_inserted += 1
            
        except Exception as e:
            summary.warnings.append(f"Failed to process item in '{metric_name}' due to: {e}. Item: {item}")
            summary.records_skipped += 1


def process_and_save_health_metrics(db: Session, payload: schemas.HealthAutoExportPayload) -> schemas.IngestResponseSummary:
    """
    Processes the entire Health Auto Export payload, saves raw data,
    and normalizes known metrics into structured tables.
    """
    summary = schemas.IngestResponseSummary(
        message="Processing completed.",
        metrics_received=len(payload.data.metrics),
        records_inserted=0,
        records_skipped=0,
        warnings=[]
    )

    # 1. Save the raw payload
    raw_payload_record = models.HealthMetricRaw(
        received_at=datetime.now(timezone.utc),
        payload_json=payload.model_dump_json()
    )
    db.add(raw_payload_record)

    # 2. Iterate through metrics and save normalized data
    known_metrics = {"resting_heart_rate", "step_count", "sleep_analysis"}
    for metric in payload.data.metrics:
        if metric.name in known_metrics:
            parse_and_save_metric(db, metric, summary)
        else:
            summary.warnings.append(f"Unknown metric type received and skipped: '{metric.name}'")
    
    # 3. We don't commit here, we let the endpoint do it after returning the summary
    # This is because the test client setup uses a single transaction that rolls back.
    # In a real app, you might commit here. For the test suite to work, we must flush.
    db.flush()
    
    return summary


def get_latest_health_summary(db: Session) -> schemas.LatestHealthSummary:
    """Retrieves a summary of the latest health metrics."""
    
    # Latest Sleep
    latest_sleep = db.query(models.SleepSession).order_by(models.SleepSession.session_end_time.desc()).first()
    
    # Latest Resting HR
    latest_hr = db.query(models.RestingHeartRate).order_by(models.RestingHeartRate.timestamp.desc()).first()
    
    start_of_today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_steps_today = db.query(func.sum(models.StepCount.value)).filter(
        models.StepCount.timestamp >= start_of_today_utc
    ).scalar() or 0.0

    return schemas.LatestHealthSummary(
        latest_sleep=latest_sleep,
        latest_resting_hr=latest_hr,
        today_steps_total=total_steps_today
    )


# --- Existing CRUD Functions (Largely untouched for backward compatibility) ---

def upsert_weather(db: Session, weather: schemas.WeatherCreate):
    db_obj = db.query(models.Weather).filter(models.Weather.date == weather.date).first()
    if db_obj:
        for key, value in weather.model_dump().items():
            setattr(db_obj, key, value)
    else:
        db_obj = models.Weather(**weather.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def upsert_daily_state(db: Session, daily_state: schemas.DailyStateCreate):
    db_obj = db.query(models.DailyState).filter(models.DailyState.date == daily_state.date).first()
    if db_obj:
        for key, value in daily_state.model_dump().items():
            setattr(db_obj, key, value)
    else:
        db_obj = models.DailyState(**daily_state.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_summary_last_n_days(db: Session, days: int = 7):
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    weather_data = {w.date: w for w in db.query(models.Weather).filter(models.Weather.date >= start_date).all()}
    health_metrics_data = {} 
    daily_state_data = {s.date: s for s in db.query(models.DailyState).filter(models.DailyState.date >= start_date).all()}

    summary_list = []
    for i in range(days):
        current_date = today - timedelta(days=i)
        health_summary = schemas.HealthMetricsSummary()
        summary_entry = schemas.SummaryData(
            date=current_date,
            weather=weather_data.get(current_date),
            health_metrics=health_summary,
            daily_state=daily_state_data.get(current_date)
        )
        summary_list.append(summary_entry)
        
    return summary_list