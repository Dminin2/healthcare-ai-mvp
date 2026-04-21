from sqlalchemy import (
    Column, Integer, Float, Date, Text, DateTime, String,
    ForeignKey, UniqueConstraint, Boolean,
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
import json
from datetime import datetime, date, timezone

from .db import Base


class JsonEncodedList(TypeDecorator):
    """Stores a Python list as a JSON-encoded TEXT column."""
    impl = Text
    cache_ok = True

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


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Weather / Environment
# ---------------------------------------------------------------------------

class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    temp_max = Column(Float, nullable=False)
    temp_min = Column(Float, nullable=False)
    precipitation_sum = Column(Float, nullable=True)
    raw_json = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Health metrics (legacy aggregated table – kept for schema continuity)
# ---------------------------------------------------------------------------

class HealthMetrics(Base):
    __tablename__ = "health_metrics"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_health_metrics_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, index=True, nullable=False)
    steps = Column(Integer, nullable=False)
    sleep_hours = Column(Float, nullable=False)
    resting_hr = Column(Integer, nullable=True)
    raw_json = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Daily state (mood / symptoms)
# ---------------------------------------------------------------------------

class DailyState(Base):
    __tablename__ = "daily_state"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_state_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, index=True, nullable=False)
    mood = Column(Integer, nullable=True)
    symptoms = Column(JsonEncodedList, nullable=True)
    notes = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Raw health payload store
# ---------------------------------------------------------------------------

class HealthMetricRaw(Base):
    __tablename__ = "health_metric_raw"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    payload_json = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# Time-series health data (Health Auto Export)
# ---------------------------------------------------------------------------

class SleepSession(Base):
    __tablename__ = "sleep_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Integer, nullable=False)
    unit = Column(String, nullable=True)
    source = Column(String, nullable=True)


class StepCount(Base):
    __tablename__ = "step_counts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    source = Column(String, nullable=True)


# ---------------------------------------------------------------------------
# Adaptive indicator thresholds (per-user)
# ---------------------------------------------------------------------------

class IndicatorThreshold(Base):
    __tablename__ = "indicator_thresholds"

    # Composite PK: one set of thresholds per (user, indicator)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    indicator_name = Column(String, primary_key=True, index=True)

    caution_threshold = Column(Float, nullable=False)
    danger_threshold = Column(Float, nullable=False)
    false_alarm_count = Column(Integer, default=0, nullable=False)
    event_at_ok_count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=False)
    last_reset_date = Column(Date, nullable=True)


# ---------------------------------------------------------------------------
# Generated advice cache
# ---------------------------------------------------------------------------

class DailyAdvice(Base):
    __tablename__ = "daily_advice"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_advice_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, index=True, nullable=False)
    overall_level = Column(String, nullable=False)
    total_points = Column(Integer, nullable=False)
    advice_text = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
