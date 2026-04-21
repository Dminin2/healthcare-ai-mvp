from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, timedelta, datetime, timezone
import json
from typing import Dict, Any, List, Optional

from . import models, schemas
from dateutil.parser import parse as dateutil_parse


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


# ---------------------------------------------------------------------------
# Health Auto Export ingest
# ---------------------------------------------------------------------------

def parse_and_save_metric(
    db: Session,
    metric: schemas.HealthMetric,
    summary: schemas.IngestResponseSummary,
    user_id: int,
):
    """Parses a single metric from the Health Auto Export payload and saves it."""
    metric_name = metric.name

    for item in metric.data:
        try:
            record_time_str_for_error = item.get("date") or item.get("sleepStart")

            if metric_name == "resting_heart_rate":
                record_time = dateutil_parse(item["date"])
                value = schemas.to_float(item.get("qty"))
                if value is None:
                    summary.warnings.append(
                        f"Could not parse 'qty' for resting_heart_rate at {record_time_str_for_error}"
                    )
                    summary.records_skipped += 1
                    continue
                db.add(models.RestingHeartRate(
                    user_id=user_id,
                    timestamp=record_time,
                    value=int(value),
                    unit=metric.units,
                    source=item.get("source"),
                ))
                summary.records_inserted += 1

            elif metric_name == "step_count":
                record_time = dateutil_parse(item["date"])
                value = schemas.to_float(item.get("qty"))
                if value is None:
                    summary.warnings.append(
                        f"Could not parse 'qty' for step_count at {record_time_str_for_error}"
                    )
                    summary.records_skipped += 1
                    continue
                db.add(models.StepCount(
                    user_id=user_id,
                    timestamp=record_time,
                    value=value,
                    unit=metric.units,
                    source=item.get("source"),
                ))
                summary.records_inserted += 1

            elif metric_name == "sleep_analysis":
                start_time = dateutil_parse(item["sleepStart"])
                end_time = dateutil_parse(item["sleepEnd"])
                db.add(models.SleepSession(
                    user_id=user_id,
                    session_start_time=start_time,
                    session_end_time=end_time,
                    total_sleep_hours=schemas.to_float(item["totalSleep"]),
                    deep_hours=schemas.to_float(item.get("deep")),
                    rem_hours=schemas.to_float(item.get("rem")),
                    core_hours=schemas.to_float(item.get("core")),
                    awake_hours=schemas.to_float(item.get("awake")),
                    source=item.get("source"),
                    raw_date_str=item["date"],
                    created_at=datetime.now(timezone.utc),
                ))
                summary.records_inserted += 1

        except Exception as e:
            summary.warnings.append(
                f"Failed to process item in '{metric_name}' due to: {e}. Item: {item}"
            )
            summary.records_skipped += 1


def process_and_save_health_metrics(
    db: Session,
    payload: schemas.HealthAutoExportPayload,
    user_id: int,
) -> schemas.IngestResponseSummary:
    summary = schemas.IngestResponseSummary(
        message="Processing completed.",
        metrics_received=len(payload.data.metrics),
        records_inserted=0,
        records_skipped=0,
        warnings=[],
    )

    db.add(models.HealthMetricRaw(
        user_id=user_id,
        received_at=datetime.now(timezone.utc),
        payload_json=payload.model_dump_json(),
    ))

    known_metrics = {"resting_heart_rate", "step_count", "sleep_analysis"}
    for metric in payload.data.metrics:
        if metric.name in known_metrics:
            parse_and_save_metric(db, metric, summary, user_id)
        else:
            summary.warnings.append(
                f"Unknown metric type received and skipped: '{metric.name}'"
            )

    db.flush()
    return summary


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def get_summary_last_n_days(
    db: Session, user_id: int, days: int = 7
) -> List[schemas.SummaryData]:
    end_date_utc = datetime.now(timezone.utc).date()

    summary_list = []
    for i in range(days):
        current_date_utc = end_date_utc - timedelta(days=i)
        start_of_day = datetime(
            current_date_utc.year, current_date_utc.month, current_date_utc.day,
            tzinfo=timezone.utc,
        )
        end_of_day = start_of_day + timedelta(days=1)

        weather_record = (
            db.query(models.Weather)
            .filter(models.Weather.date == current_date_utc)
            .first()
        )
        daily_state_record = (
            db.query(models.DailyState)
            .filter(models.DailyState.user_id == user_id, models.DailyState.date == current_date_utc)
            .first()
        )

        total_steps = db.query(func.sum(models.StepCount.value)).filter(
            models.StepCount.user_id == user_id,
            models.StepCount.timestamp >= start_of_day,
            models.StepCount.timestamp < end_of_day,
        ).scalar()

        avg_resting_hr = db.query(func.avg(models.RestingHeartRate.value)).filter(
            models.RestingHeartRate.user_id == user_id,
            models.RestingHeartRate.timestamp >= start_of_day,
            models.RestingHeartRate.timestamp < end_of_day,
        ).scalar()
        if avg_resting_hr is not None:
            avg_resting_hr = round(avg_resting_hr, 1)

        total_sleep_hours = db.query(func.sum(models.SleepSession.total_sleep_hours)).filter(
            models.SleepSession.user_id == user_id,
            func.date(models.SleepSession.session_end_time) == current_date_utc,
        ).scalar()
        if total_sleep_hours is not None:
            total_sleep_hours = round(total_sleep_hours, 2)

        health_metrics_summary = schemas.HealthMetricsSummary(
            steps=int(total_steps) if total_steps is not None else None,
            sleep_hours=total_sleep_hours,
            resting_hr=avg_resting_hr,
        )

        summary_list.append(schemas.SummaryData(
            date=current_date_utc,
            weather=weather_record,
            daily_state=daily_state_record,
            health_metrics=(
                health_metrics_summary
                if any([health_metrics_summary.steps,
                        health_metrics_summary.sleep_hours,
                        health_metrics_summary.resting_hr])
                else None
            ),
        ))

    return summary_list


# ---------------------------------------------------------------------------
# Weather / DailyState upsert
# ---------------------------------------------------------------------------

def upsert_weather(db: Session, weather: schemas.WeatherCreate) -> models.Weather:
    db_obj = (
        db.query(models.Weather)
        .filter(models.Weather.date == weather.date)
        .first()
    )
    if db_obj:
        for key, value in weather.model_dump().items():
            setattr(db_obj, key, value)
    else:
        db_obj = models.Weather(**weather.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def upsert_daily_state(
    db: Session, daily_state: schemas.DailyStateCreate, user_id: int
) -> models.DailyState:
    db_obj = (
        db.query(models.DailyState)
        .filter(models.DailyState.user_id == user_id, models.DailyState.date == daily_state.date)
        .first()
    )
    if db_obj:
        for key, value in daily_state.model_dump().items():
            setattr(db_obj, key, value)
    else:
        db_obj = models.DailyState(**daily_state.model_dump(), user_id=user_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# ---------------------------------------------------------------------------
# Analysis: date-range queries (all filtered by user_id)
# ---------------------------------------------------------------------------

def get_weather_for_date_range(
    db: Session, start_date: date, end_date: date
) -> List[models.Weather]:
    return (
        db.query(models.Weather)
        .filter(models.Weather.date.between(start_date, end_date))
        .order_by(models.Weather.date.asc())
        .all()
    )


def get_daily_states_for_date_range(
    db: Session, user_id: int, start_date: date, end_date: date
) -> List[models.DailyState]:
    return (
        db.query(models.DailyState)
        .filter(
            models.DailyState.user_id == user_id,
            models.DailyState.date.between(start_date, end_date),
        )
        .order_by(models.DailyState.date.asc())
        .all()
    )


def get_aggregated_health_metrics_for_date(
    db: Session, user_id: int, target_date: date
) -> schemas.HealthMetricsSummary:
    start_of_day = datetime(
        target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
    )
    end_of_day = start_of_day + timedelta(days=1)

    total_steps = db.query(func.sum(models.StepCount.value)).filter(
        models.StepCount.user_id == user_id,
        models.StepCount.timestamp >= start_of_day,
        models.StepCount.timestamp < end_of_day,
    ).scalar()

    avg_resting_hr = db.query(func.avg(models.RestingHeartRate.value)).filter(
        models.RestingHeartRate.user_id == user_id,
        models.RestingHeartRate.timestamp >= start_of_day,
        models.RestingHeartRate.timestamp < end_of_day,
    ).scalar()
    if avg_resting_hr is not None:
        avg_resting_hr = round(avg_resting_hr, 1)

    total_sleep_hours = db.query(func.sum(models.SleepSession.total_sleep_hours)).filter(
        models.SleepSession.user_id == user_id,
        func.date(models.SleepSession.session_end_time) == target_date,
    ).scalar()
    if total_sleep_hours is not None:
        total_sleep_hours = round(total_sleep_hours, 2)

    return schemas.HealthMetricsSummary(
        steps=int(total_steps) if total_steps is not None else None,
        sleep_hours=total_sleep_hours,
        resting_hr=avg_resting_hr,
    )


# ---------------------------------------------------------------------------
# Indicator thresholds (per-user, composite PK)
# ---------------------------------------------------------------------------

def get_indicator_thresholds(
    db: Session, user_id: int
) -> Dict[str, models.IndicatorThreshold]:
    thresholds = (
        db.query(models.IndicatorThreshold)
        .filter(models.IndicatorThreshold.user_id == user_id)
        .all()
    )
    return {t.indicator_name: t for t in thresholds}


def upsert_indicator_threshold(
    db: Session, threshold_data: models.IndicatorThreshold
) -> models.IndicatorThreshold:
    merged = db.merge(threshold_data)
    db.commit()
    return merged


# ---------------------------------------------------------------------------
# Daily advice cache
# ---------------------------------------------------------------------------

def get_daily_advice_by_date(
    db: Session, user_id: int, advice_date: date
) -> Optional[models.DailyAdvice]:
    return (
        db.query(models.DailyAdvice)
        .filter(
            models.DailyAdvice.user_id == user_id,
            models.DailyAdvice.date == advice_date,
        )
        .first()
    )


def upsert_daily_advice(
    db: Session, user_id: int, advice: schemas.DailyAdviceCreate
) -> models.DailyAdvice:
    db_obj = (
        db.query(models.DailyAdvice)
        .filter(
            models.DailyAdvice.user_id == user_id,
            models.DailyAdvice.date == advice.date,
        )
        .first()
    )
    if db_obj:
        db_obj.overall_level = advice.overall_level
        db_obj.total_points = advice.total_points
        db_obj.advice_text = advice.advice_text
        db_obj.source = advice.source
    else:
        db_obj = models.DailyAdvice(
            **advice.model_dump(),
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
        )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
