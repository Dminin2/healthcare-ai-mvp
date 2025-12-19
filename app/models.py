from sqlalchemy import Column, Integer, Float, Date, Text
from sqlalchemy.types import TypeDecorator
import json
from .db import Base

class JsonEncodedList(TypeDecorator):
    """Enables storing a list of strings as a JSON-encoded string in a TEXT field."""
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
