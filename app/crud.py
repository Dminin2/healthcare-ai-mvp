from sqlalchemy.orm import Session
from sqlalchemy import func, and_
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
            # For RHR and StepCount, 'date' is timestamp. For Sleep, 'sleepStart' is timestamp.
            # Use 'date' if available, otherwise 'sleepStart' for error reporting context.
            record_time_str_for_error = item.get("date") or item.get("sleepStart")
            
            if metric_name == "resting_heart_rate":
                record_time = dateutil_parse(item["date"])
                value = schemas.to_float(item.get("qty"))
                if value is None:
                    summary.warnings.append(f"Could not parse 'qty' for resting_heart_rate at {record_time_str_for_error}")
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
                record_time = dateutil_parse(item["date"])
                value = schemas.to_float(item.get("qty"))
                if value is None:
                    summary.warnings.append(f"Could not parse 'qty' for step_count at {record_time_str_for_error}")
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


# --- Rewritten get_summary_last_n_days for integrated summary ---

def get_summary_last_n_days(db: Session, days: int = 7) -> List[schemas.SummaryData]:
    end_date_utc = datetime.now(timezone.utc).date() # Today's date in UTC
    
    summary_list = []
    for i in range(days):
        current_date_utc = end_date_utc - timedelta(days=i)
        
        # Start and end of the current UTC day
        start_of_current_day_utc = datetime(current_date_utc.year, current_date_utc.month, current_date_utc.day, tzinfo=timezone.utc)
        end_of_current_day_utc = start_of_current_day_utc + timedelta(days=1)
        
        # --- Query Weather and DailyState ---
        weather_record = db.query(models.Weather).filter(models.Weather.date == current_date_utc).first()
        daily_state_record = db.query(models.DailyState).filter(models.DailyState.date == current_date_utc).first()
        
        # --- Aggregate Health Metrics ---
        # 1. Steps: Sum for the current UTC day
        total_steps = db.query(func.sum(models.StepCount.value)).filter(
            and_(
                models.StepCount.timestamp >= start_of_current_day_utc,
                models.StepCount.timestamp < end_of_current_day_utc
            )
        ).scalar()

        # 2. Resting HR: Average for the current UTC day
        avg_resting_hr = db.query(func.avg(models.RestingHeartRate.value)).filter(
            and_(
                models.RestingHeartRate.timestamp >= start_of_current_day_utc,
                models.RestingHeartRate.timestamp < end_of_current_day_utc
            )
        ).scalar()
        if avg_resting_hr is not None:
            avg_resting_hr = round(avg_resting_hr, 1) # Round to 1 decimal place

        # 3. Sleep Hours: Sum for sessions ending on the current UTC day
        total_sleep_hours = db.query(func.sum(models.SleepSession.total_sleep_hours)).filter(
            and_(
                func.date(models.SleepSession.session_end_time) == current_date_utc # Match end date with current_date_utc
            )
        ).scalar()
        if total_sleep_hours is not None:
            total_sleep_hours = round(total_sleep_hours, 2) # Round to 2 decimal places

        health_metrics_summary = schemas.HealthMetricsSummary(
            steps=int(total_steps) if total_steps is not None else None,
            sleep_hours=total_sleep_hours,
            resting_hr=avg_resting_hr
        )

        # --- Construct SummaryData ---
        summary_entry = schemas.SummaryData(
            date=current_date_utc,
            weather=weather_record,
            daily_state=daily_state_record,
            health_metrics=health_metrics_summary if any([health_metrics_summary.steps, health_metrics_summary.sleep_hours, health_metrics_summary.resting_hr]) else None
        )
        summary_list.append(summary_entry)
        
    return summary_list


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