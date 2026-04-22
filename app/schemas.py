from pydantic import BaseModel, ConfigDict, field_validator, Field, EmailStr
from datetime import date, datetime
from typing import Optional, List, Union, Any, Dict
from enum import Enum


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: str
    password: str

class UserRead(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SymptomCode(str, Enum):
    HEADACHE = "headache"
    FATIGUE = "fatigue"
    NAUSEA = "nausea"
    FEVER = "fever"
    SORE_THROAT = "sore_throat"
    BODY_ACHE = "body_ache"
    NONE = "none"


# ---------------------------------------------------------------------------
# Weather schemas
# ---------------------------------------------------------------------------

class WeatherBase(BaseModel):
    temp_max: float
    temp_min: float
    precipitation_sum: Optional[float] = None

class WeatherCreate(WeatherBase):
    date: date
    raw_json: Optional[str] = None

class Weather(WeatherBase):
    id: int
    date: date
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Daily state schemas
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Health Auto Export ingest schemas
# ---------------------------------------------------------------------------

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

class HealthMetric(BaseModel):
    name: str
    units: Optional[str] = None
    data: List[Dict[str, Any]]

class HealthData(BaseModel):
    metrics: List[HealthMetric]

class HealthAutoExportPayload(BaseModel):
    data: HealthData

class IngestResponseSummary(BaseModel):
    message: str
    metrics_received: int
    records_inserted: int
    records_skipped: int
    warnings: List[str] = []


# ---------------------------------------------------------------------------
# Summary schemas (GET /summary/last7d)
# ---------------------------------------------------------------------------

class HealthMetricsSummary(BaseModel):
    steps: Optional[int] = None
    sleep_hours: Optional[float] = None
    resting_hr: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

class WeatherSummary(WeatherBase):
    model_config = ConfigDict(from_attributes=True)

class DailyStateSummary(DailyStateBase):
    model_config = ConfigDict(from_attributes=True)

class SummaryData(BaseModel):
    date: date
    weather: Optional[WeatherSummary] = None
    health_metrics: Optional[HealthMetricsSummary] = None
    daily_state: Optional[DailyStateSummary] = None


# ---------------------------------------------------------------------------
# Analysis schemas
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Daily advice schemas
# ---------------------------------------------------------------------------

class DailyAdviceBase(BaseModel):
    overall_level: str
    total_points: int
    advice_text: str
    source: str

class DailyAdviceCreate(DailyAdviceBase):
    date: date

class DailyAdvice(DailyAdviceBase):
    id: int
    date: date
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AdviceResponse(BaseModel):
    date: date
    overall_level: str
    total_points: int
    advice: str
