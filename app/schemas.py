from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import date, datetime
from typing import Optional, List, Union, Any, Dict
from enum import Enum

# Utility function for parsing inconsistent number formats
def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# --- Enums (Existing) ---
class SymptomCode(str, Enum):
    HEADACHE = "headache"
    FATIGUE = "fatigue"
    NAUSEA = "nausea"
    FEVER = "fever"
    SORE_THROAT = "sore_throat"
    BODY_ACHE = "body_ache"
    NONE = "none"

# --- Existing Schemas (Untouched) ---
class WeatherBase(BaseModel):
    temp_max: float
    temp_min: float
    precipitation_sum: Optional[float] = None
# ... (and other existing schemas like DailyState)

# --- NEW Schemas for Health Auto Export ---

# 1. Schemas for specific metric data points
class QuantityMetricData(BaseModel):
    date: str
    qty: Union[float, int, str]
    source: Optional[str] = None

class SleepAnalysisData(BaseModel):
    date: str
    sleepStart: str
    sleepEnd: str
    totalSleep: Union[float, str]
    deep: Optional[Union[float, str]] = None
    core: Optional[Union[float, str]] = None
    rem: Optional[Union[float, str]] = None
    awake: Optional[Union[float, str]] = None
    source: Optional[str] = None

# 2. A generic container for a single metric
class HealthMetric(BaseModel):
    name: str
    units: Optional[str] = None
    data: List[Dict[str, Any]]

# 3. The top-level payload structure
class HealthData(BaseModel):
    metrics: List[HealthMetric]

class HealthAutoExportPayload(BaseModel):
    data: HealthData

# 4. Schema for the response summary of the ingest endpoint
class IngestResponseSummary(BaseModel):
    message: str
    metrics_received: int
    records_inserted: int
    records_skipped: int
    warnings: List[str] = []

# --- Schemas to be removed or replaced ---
# The old HealthMetrics schemas are now obsolete for the ingest endpoint.
# We keep them here commented out for reference but they are no longer used
# by the new implementation.

# class HealthMetricsBase(BaseModel):
#     steps: int
#     sleep_hours: float
#     resting_hr: Optional[int] = None

# class HealthMetricsCreate(HealthMetricsBase):
#     date: date
#     raw_json: Optional[str] = None

# class HealthMetrics(HealthMetricsBase):
#     id: int
#     date: date
#     model_config = ConfigDict(from_attributes=True)
    
# We need to keep the summary schema for the existing GET /summary/last7d endpoint
class HealthMetricsSummary(BaseModel):
    steps: Optional[int] = None
    sleep_hours: Optional[float] = None
    resting_hr: Optional[float] = None # Change from int to float for average
    model_config = ConfigDict(from_attributes=True)

# We need to keep DailyState and Weather for the existing endpoints
class DailyStateBase(BaseModel):
    mood: Optional[int] = None
    symptoms: Optional[List[SymptomCode]] = None
    notes: Optional[str] = None
    
class DailyStateCreate(DailyStateBase):
    date: date
    raw_json: Optional[str] = None

class DailyState(DailyStateBase):
    id: int
    date: date
    model_config = ConfigDict(from_attributes=True)

class WeatherCreate(WeatherBase):
    date: date
    raw_json: Optional[str] = None
    
class Weather(WeatherBase):
    id: int
    date: date
    model_config = ConfigDict(from_attributes=True)

# --- Summary Schemas for GET /summary/last7d (Existing, but check compatibility) ---
class WeatherSummary(WeatherBase):
    model_config = ConfigDict(from_attributes=True)

class DailyStateSummary(DailyStateBase):
    model_config = ConfigDict(from_attributes=True)

class SummaryData(BaseModel):
    date: date
    weather: Optional[WeatherSummary] = None
    health_metrics: Optional[HealthMetricsSummary] = None
    daily_state: Optional[DailyStateSummary] = None


# --- NEW Schemas for Analysis Endpoint ---

class IndicatorResult(BaseModel):
    name: str
    label: str  # "ok", "caution", "danger"
    value: Optional[float] = None
    unit: Optional[str] = None
    related_symptoms: List[str] = Field(default_factory=list)

class AnalysisEvidence(BaseModel):
    rules_triggered: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    date: date
    overall_level: str  # "ok", "caution", "danger"
    total_points: int
    indicators: List[IndicatorResult]
    event_rates: Dict[str, Dict[str, Optional[float]]] = Field(default_factory=dict)
    evidence: AnalysisEvidence = Field(default_factory=AnalysisEvidence)
