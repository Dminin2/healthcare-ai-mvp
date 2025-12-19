from sqlalchemy.orm import Session
from datetime import date, timedelta
import json

from . import models, schemas

def _upsert(db: Session, model_cls, schema_obj, date_val):
    """Generic upsert function."""
    # If raw_json is not provided, create it from the schema object
    if hasattr(schema_obj, 'raw_json') and schema_obj.raw_json is None:
        # Create a dict from the schema, excluding the raw_json field itself, and dump to string
        dump_dict = schema_obj.model_dump(exclude={'raw_json'})
        # Ensure date is in string format for JSON
        dump_dict['date'] = dump_dict['date'].isoformat()
        schema_obj.raw_json = json.dumps(dump_dict)

    values = schema_obj.model_dump()
    
    existing_obj = db.query(model_cls).filter(model_cls.date == date_val).first()

    if existing_obj:
        # Update
        for key, value in values.items():
            setattr(existing_obj, key, value)
        db_obj = existing_obj
    else:
        # Create
        db_obj = model_cls(**values)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def upsert_weather(db: Session, weather: schemas.WeatherCreate):
    return _upsert(db, models.Weather, weather, weather.date)

def upsert_health_metrics(db: Session, health_metrics: schemas.HealthMetricsCreate):
    return _upsert(db, models.HealthMetrics, health_metrics, health_metrics.date)

def upsert_daily_state(db: Session, daily_state: schemas.DailyStateCreate):
    return _upsert(db, models.DailyState, daily_state, daily_state.date)


def get_summary_last_n_days(db: Session, days: int = 7):
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # Fetch data and create mappings
    weather_data = {w.date: w for w in db.query(models.Weather).filter(models.Weather.date >= start_date).all()}
    health_metrics_data = {h.date: h for h in db.query(models.HealthMetrics).filter(models.HealthMetrics.date >= start_date).all()}
    daily_state_data = {s.date: s for s in db.query(models.DailyState).filter(models.DailyState.date >= start_date).all()}

    summary_list = []
    # Loop from most recent day to oldest
    for i in range(days):
        current_date = today - timedelta(days=i)
        summary_entry = schemas.SummaryData(
            date=current_date,
            weather=weather_data.get(current_date),
            health_metrics=health_metrics_data.get(current_date),
            daily_state=daily_state_data.get(current_date)
        )
        summary_list.append(summary_entry)
        
    return summary_list