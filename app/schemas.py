from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional

# --- Base Schemas (for shared properties, NO date/id) ---
class WeatherBase(BaseModel):
    temp_max: float
    temp_min: float
    precipitation_sum: Optional[float] = None

class HealthMetricsBase(BaseModel):
    steps: int
    sleep_hours: float
    resting_hr: Optional[int] = None

class DailyStateBase(BaseModel):
    mood: Optional[int] = None
    symptoms: Optional[str] = None
    notes: Optional[str] = None

# --- Create Schemas (for POST /ingest, includes date) ---
class WeatherCreate(WeatherBase):
    date: date
    raw_json: Optional[str] = None

class HealthMetricsCreate(HealthMetricsBase):
    date: date
    raw_json: Optional[str] = None

class DailyStateCreate(DailyStateBase):
    date: date
    raw_json: Optional[str] = None

# --- ORM Schemas (for internal use, e.g., reading from DB, includes id and date) ---
class Weather(WeatherBase):
    id: int
    date: date
    model_config = ConfigDict(from_attributes=True)

class HealthMetrics(HealthMetricsBase):
    id: int
    date: date
    model_config = ConfigDict(from_attributes=True)

class DailyState(DailyStateBase):
    id: int
    date: date
    model_config = ConfigDict(from_attributes=True)


# --- Summary Schemas (for GET /summary/last7d response) ---
class WeatherSummary(WeatherBase):
    model_config = ConfigDict(from_attributes=True)

class HealthMetricsSummary(HealthMetricsBase):
    model_config = ConfigDict(from_attributes=True)

class DailyStateSummary(DailyStateBase):
    model_config = ConfigDict(from_attributes=True)

class SummaryData(BaseModel):
    date: date
    weather: Optional[WeatherSummary] = None
    health_metrics: Optional[HealthMetricsSummary] = None
    daily_state: Optional[DailyStateSummary] = None