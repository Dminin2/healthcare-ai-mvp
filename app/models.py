from sqlalchemy import Column, Integer, Float, Date, Text, DateTime, String
from sqlalchemy.types import TypeDecorator
import json
from datetime import datetime, date, timezone # Added imports
from .db import Base

# This TypeDecorator is from a previous implementation.
# It is kept for compatibility with the 'symptoms' field in DailyState,
# but is not actively used by the new health metric models.
class JsonEncodedList(TypeDecorator):
    """Enables storing a list as a JSON-encoded string in a TEXT field."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [value] if isinstance(value, str) else []
        return value

# --- Existing Models (Largely untouched) ---

class Weather(Base):
    __tablename__ = "weather"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    temp_max = Column(Float, nullable=False)
    temp_min = Column(Float, nullable=False)
    precipitation_sum = Column(Float, nullable=True)
    raw_json = Column(Text, nullable=True)

class HealthMetrics(Base):
    __tablename__ = "health_metrics"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    steps = Column(Integer, nullable=False)
    sleep_hours = Column(Float, nullable=False)
    resting_hr = Column(Integer, nullable=True)
    raw_json = Column(Text, nullable=True)

class DailyState(Base):
    __tablename__ = "daily_state"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    mood = Column(Integer, nullable=True)
    symptoms = Column(JsonEncodedList, nullable=True)
    notes = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)


# --- NEW Models for Health Auto Export Data ---

class HealthMetricRaw(Base):
    __tablename__ = "health_metric_raw"
    id = Column(Integer, primary_key=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    payload_json = Column(Text, nullable=False)

class SleepSession(Base):
    __tablename__ = "sleep_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    session_end_time = Column(DateTime(timezone=True), nullable=False)
    total_sleep_hours = Column(Float, nullable=False)
    deep_hours = Column(Float, nullable=True)
    rem_hours = Column(Float, nullable=True)
    core_hours = Column(Float, nullable=True)
    awake_hours = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    raw_date_str = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

class RestingHeartRate(Base):
    __tablename__ = "resting_heart_rates"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Integer, nullable=False)
    unit = Column(String, nullable=True)
    source = Column(String, nullable=True)

class StepCount(Base):

    __tablename__ = "step_counts"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    value = Column(Float, nullable=False)

    unit = Column(String, nullable=True)

    source = Column(String, nullable=True)





class IndicatorThreshold(Base):





    __tablename__ = "indicator_thresholds"





    indicator_name = Column(String, primary_key=True, index=True)





    caution_threshold = Column(Float, nullable=False)





    danger_threshold = Column(Float, nullable=False)





    # The following are for the auto-adjustment logic





    false_alarm_count = Column(Integer, default=0, nullable=False)





    event_at_ok_count = Column(Integer, default=0, nullable=False)





    last_updated = Column(DateTime(timezone=True), nullable=False)





    last_reset_date = Column(Date, nullable=True)











class DailyAdvice(Base):





    __tablename__ = "daily_advice"





    id = Column(Integer, primary_key=True, index=True)





    date = Column(Date, unique=True, index=True, nullable=False)





    overall_level = Column(String, nullable=False) # e.g., "ok", "caution", "danger"





    total_points = Column(Integer, nullable=False)





    advice_text = Column(Text, nullable=False)





    source = Column(String, nullable=False) # "gemini" or "fallback"





    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
