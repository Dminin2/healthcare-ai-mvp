from sqlalchemy import Column, Integer, String, Float, Date, Text
from .db import Base

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
    symptoms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)
