# ruff: noqa: E722
from datetime import date, timedelta, datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
import numpy as np
import math
from collections import Counter

from .. import crud, models, schemas

# --- 1. Constants and Configuration ---

class IndicatorName:
    HIGH_TEMPERATURE = "high_temperature"
    LOW_TEMPERATURE = "low_temperature"
    PRECIPITATION = "precipitation"
    TEMPERATURE_CHANGE = "temperature_change"
    HIGH_ACTIVITY = "high_activity"
    SLEEP_DEFICIT = "sleep_deficit"
    ELEVATED_RESTING_HR = "elevated_resting_hr"
    FATIGUE_LOAD = "fatigue_load"

class Label:
    OK = "ok"
    CAUTION = "caution"
    DANGER = "danger"

INITIAL_THRESHOLDS = {
    IndicatorName.HIGH_TEMPERATURE: {"caution": 30.0, "danger": 33.0, "unit": "°C"},
    IndicatorName.LOW_TEMPERATURE: {"caution": 5.0, "danger": 0.0, "unit": "°C"},
    IndicatorName.PRECIPITATION: {"caution": 5.0, "danger": 20.0, "unit": "mm"},
    IndicatorName.TEMPERATURE_CHANGE: {"caution": 4.0, "danger": 7.0, "unit": "°C"},
    IndicatorName.HIGH_ACTIVITY: {"caution": 1.0, "danger": 1.5, "unit": "σ"},
    IndicatorName.SLEEP_DEFICIT: {"caution": 6.0, "danger": 5.0, "unit": "h"},
    IndicatorName.ELEVATED_RESTING_HR: {"caution": 5.0, "danger": 10.0, "unit": "bpm"},
}

ADJUSTMENT_PARAMS = {
    "lookback_days": 30,
    "false_alarm_limit": 5,
    "event_at_ok_limit": 3,
    "deltas": {
        IndicatorName.HIGH_TEMPERATURE: 0.5,
        IndicatorName.LOW_TEMPERATURE: -0.5,
        IndicatorName.PRECIPITATION: 1.0,
        IndicatorName.TEMPERATURE_CHANGE: 0.5,
        IndicatorName.HIGH_ACTIVITY: 0.1, # For sigma-based metric
        IndicatorName.SLEEP_DEFICIT: -0.25,
        IndicatorName.ELEVATED_RESTING_HR: 1.0,
    }
}
ANALYSIS_HISTORY_DAYS = 30

# --- 2. Main Orchestration Function ---

def run_daily_analysis(db_session: Session, analysis_date: date) -> Optional[schemas.AnalysisResult]:
    thresholds = _initialize_thresholds(db_session)
    start_date = analysis_date - timedelta(days=ANALYSIS_HISTORY_DAYS + 8)
    
    try:
        raw_weather = crud.get_weather_for_date_range(db_session, start_date, analysis_date)
        raw_daily_states = crud.get_daily_states_for_date_range(db_session, start_date, analysis_date)
        raw_health_metrics = {
            d: crud.get_aggregated_health_metrics_for_date(db_session, d)
            for d in (start_date + timedelta(days=i) for i in range((analysis_date - start_date).days + 1))
        }
    except Exception as e:
        print(f"Error fetching data for analysis: {e}")
        return None

    analysis_data = _normalize_data(raw_weather, raw_health_metrics, raw_daily_states)
    
    missing_fields = _get_missing_fields(analysis_data, analysis_date)
    if "Core data for today or yesterday" in missing_fields:
        return schemas.AnalysisResult(
            date=analysis_date, overall_level=Label.OK, total_points=0, indicators=[],
            evidence=schemas.AnalysisEvidence(missing_fields=missing_fields)
        )

    full_historical_analysis = {}
    for i in range(ANALYSIS_HISTORY_DAYS + 1):
        d = analysis_date - timedelta(days=i)
        if d in analysis_data and d not in full_historical_analysis:
            vals = _calculate_all_indicators(analysis_data, d)
            inds = _evaluate_indicator_levels(vals, thresholds, analysis_data, d)
            evt = _define_event(analysis_data.get(d, {}))
            full_historical_analysis[d] = {"indicators": {i.name: i for i in inds}, "event": evt}
    
    symptom_analysis = _analyze_symptom_correlation(full_historical_analysis, analysis_data)
    event_rates = _calculate_event_rates(full_historical_analysis)
    
    # Adjust thresholds based on today's data.
    _adjust_thresholds(db_session, thresholds, full_historical_analysis, analysis_date)
    db_session.commit() # Commit changes made by threshold adjustment and initialization

    today_analysis = full_historical_analysis.get(analysis_date)
    if not today_analysis:
        missing_fields.append("Analysis could not be computed for today.")
        return schemas.AnalysisResult(date=analysis_date, overall_level=Label.OK, total_points=0, indicators=[], evidence=schemas.AnalysisEvidence(missing_fields=missing_fields))

    points = 0
    forecast_indicators = {
        IndicatorName.HIGH_TEMPERATURE, IndicatorName.LOW_TEMPERATURE,
        IndicatorName.PRECIPITATION, IndicatorName.TEMPERATURE_CHANGE,
        IndicatorName.SLEEP_DEFICIT
    }
    
    final_indicators = []
    for name, ind in today_analysis["indicators"].items():
        if name in forecast_indicators:
            if ind.label == Label.CAUTION: points += 1
            elif ind.label == Label.DANGER: points += 2
        ind.related_symptoms = symptom_analysis.get(name, [])
        final_indicators.append(ind)

    overall_level = Label.OK
    if points >= 3: overall_level = Label.DANGER
    elif points >= 1: overall_level = Label.CAUTION
        
    return schemas.AnalysisResult(
        date=analysis_date, overall_level=overall_level, total_points=points,
        indicators=sorted(final_indicators, key=lambda x: x.name),
        event_rates=event_rates, evidence=schemas.AnalysisEvidence(missing_fields=missing_fields)
    )

# --- 3. Helper Functions (Data Prep & Calc) ---
# Unchanged...
def _initialize_thresholds(db: Session) -> Dict[str, models.IndicatorThreshold]:
    current_thresholds = crud.get_indicator_thresholds(db)
    updated = False
    for name, values in INITIAL_THRESHOLDS.items():
        if name not in current_thresholds:
            threshold_obj = models.IndicatorThreshold(
                indicator_name=name, caution_threshold=values["caution"],
                danger_threshold=values["danger"], last_updated=datetime.now(timezone.utc)
            )
            crud.upsert_indicator_threshold(db, threshold_obj) # This commits the individual upsert
            updated = True
    if updated:
        db.commit() # Commit the new thresholds here if there were updates
    return crud.get_indicator_thresholds(db)

def _normalize_data(weather, health, states) -> Dict[date, Dict[str, Any]]:
    normalized = {}
    for w in weather:
        normalized.setdefault(w.date, {})
        normalized[w.date].update({"max_temp_c": w.temp_max, "min_temp_c": w.temp_min, "precip_mm": w.precipitation_sum})
    for d, h in health.items():
        if h:
            normalized.setdefault(d, {})
            normalized[d].update({"steps": h.steps, "sleep_hours": h.sleep_hours, "resting_hr": h.resting_hr})
    for s in states:
        normalized.setdefault(s.date, {})
        normalized[s.date].update({"mood": s.mood, "symptoms": s.symptoms or [], "notes": s.notes})
    return normalized

def _get_missing_fields(analysis_data: Dict, analysis_date: date) -> List[str]:
    missing, today, yesterday = [], analysis_data.get(analysis_date, {}), analysis_data.get(analysis_date - timedelta(days=1), {})
    required = {"today": ["max_temp_c", "min_temp_c", "precip_mm", "sleep_hours"], "yesterday": ["max_temp_c"]}
    if not all(k in today for k in required["today"]) or not all(k in yesterday for k in required["yesterday"]):
        missing.append("Core data for today or yesterday")
    return missing

def _calculate_all_indicators(data: Dict[date, Dict], today: date) -> Dict[str, Optional[float]]:
    values, today_data, yesterday_data = {}, data.get(today, {}), data.get(today - timedelta(days=1), {})
    values.update({
        IndicatorName.HIGH_TEMPERATURE: today_data.get("max_temp_c"),
        IndicatorName.LOW_TEMPERATURE: today_data.get("min_temp_c"),
        IndicatorName.PRECIPITATION: today_data.get("precip_mm"),
        IndicatorName.SLEEP_DEFICIT: today_data.get("sleep_hours"),
        IndicatorName.TEMPERATURE_CHANGE: abs(today_data["max_temp_c"] - yesterday_data["max_temp_c"]) if "max_temp_c" in today_data and "max_temp_c" in yesterday_data else None
    })
    def get_past(metric: str, days: int): return [data.get(today - timedelta(i), {}).get(metric) for i in range(1, days + 1) if data.get(today - timedelta(i), {}).get(metric) is not None]
    past_steps = get_past("steps", 7)
    values[IndicatorName.HIGH_ACTIVITY] = ((today_data["steps"] - np.mean(past_steps)) / np.std(past_steps)) if today_data.get("steps") and len(past_steps) >= 3 and np.std(past_steps) > 0 else (0.0 if today_data.get("steps") else None)
    past_hr = get_past("resting_hr", 7)
    values[IndicatorName.ELEVATED_RESTING_HR] = (today_data["resting_hr"] - np.mean(past_hr)) if today_data.get("resting_hr") and len(past_hr) >= 3 else None
    return values

def _evaluate_indicator_levels(calculated_values: Dict, thresholds: Dict, data: Dict, today: date) -> List[schemas.IndicatorResult]:
    evaluated = {}
    for name, value in calculated_values.items():
        label, unit = Label.OK, INITIAL_THRESHOLDS.get(name, {}).get("unit")
        if value is None: evaluated[name] = schemas.IndicatorResult(name=name, label=Label.OK, value=value, unit=unit); continue
        thresh = thresholds.get(name)
        if not thresh: evaluated[name] = schemas.IndicatorResult(name=name, label=Label.OK, value=round(value, 2), unit=unit); continue
        if name in [IndicatorName.LOW_TEMPERATURE, IndicatorName.SLEEP_DEFICIT]:
            if value <= thresh.danger_threshold: label = Label.DANGER
            elif value <= thresh.caution_threshold: label = Label.CAUTION
        else:
            if value >= thresh.danger_threshold: label = Label.DANGER
            elif value >= thresh.caution_threshold: label = Label.CAUTION
        evaluated[name] = schemas.IndicatorResult(name=name, label=label, value=round(value, 2), unit=unit)
    ha_label, sd_label = evaluated.get(IndicatorName.HIGH_ACTIVITY, schemas.IndicatorResult(name="", label=Label.OK)).label, evaluated.get(IndicatorName.SLEEP_DEFICIT, schemas.IndicatorResult(name="", label=Label.OK)).label
    fatigue_label = Label.DANGER if ha_label == Label.DANGER and sd_label == Label.DANGER else (Label.CAUTION if ha_label != Label.OK and sd_label != Label.OK else Label.OK)
    evaluated[IndicatorName.FATIGUE_LOAD] = schemas.IndicatorResult(name=IndicatorName.FATIGUE_LOAD, label=fatigue_label, value=None, unit=None)
    return list(evaluated.values())

# --- 4. Historical Analysis Helpers ---

def _define_event(day_data: Dict) -> bool:
    if not day_data: return False
    return any(s and s != "none" for s in day_data.get("symptoms", [])) or (day_data.get("mood") is not None and day_data["mood"] <= 2)

def _analyze_symptom_correlation(historical_analysis: Dict, analysis_data: Dict) -> Dict[str, List[str]]:
    # Correctly get the string values of the indicator names
    indicator_names = [value for key, value in vars(IndicatorName).items() if not key.startswith('__')]
    
    symptom_counts = Counter(s for d in analysis_data.values() for s in d.get("symptoms", []) if s and s != "none")
    relevant_symptoms = {s for s, count in symptom_counts.items() if count >= 3}
    if not relevant_symptoms: return {}
    
    p_symptom_alert, p_symptom_ok = {n: Counter() for n in indicator_names}, {n: Counter() for n in indicator_names}
    alert_days, ok_days = Counter(), Counter()
    
    for date, day in historical_analysis.items():
        symptoms = set(analysis_data.get(date, {}).get("symptoms", []))
        if not any(symptoms) or "none" in symptoms:
            symptoms = set() # Ensure it's an empty set if no real symptoms
            
        for name, ind in day["indicators"].items():
            if ind.label != Label.OK:
                alert_days[name] += 1
                for s in symptoms: p_symptom_alert[name].update([s])
            else:
                ok_days[name] += 1
                for s in symptoms: p_symptom_ok[name].update([s])

    scores = {n: {} for n in indicator_names}
    for name in indicator_names:
        for s in relevant_symptoms:
            p_alert = p_symptom_alert[name][s] / alert_days[name] if alert_days[name] > 0 else 0
            p_ok = p_symptom_ok[name][s] / ok_days[name] if ok_days[name] > 0 else 0
            if (p_alert - p_ok) > 0.1: scores[name][s] = p_alert - p_ok
            
    return {name: [s[0] for s in sorted(sc.items(), key=lambda i: i[1], reverse=True)[:3]] for name, sc in scores.items()}

def _calculate_event_rates(historical_analysis: Dict) -> Dict[str, Dict[str, Optional[float]]]:
    event_counts, total_counts = Counter(), Counter()
    for day in historical_analysis.values():
        for name, ind in day["indicators"].items():
            key = (name, ind.label); total_counts[key] += 1
            if day["event"]: event_counts[key] += 1
    rates = {}
    for (name, label), total in total_counts.items():
        rates.setdefault(name, {})[label] = round(event_counts.get((name, label), 0) / total, 3) if total > 0 else None
    return rates

# --- 5. Threshold Adjustment Helper ---

def _adjust_thresholds(db: Session, thresholds: Dict[str, models.IndicatorThreshold], historical_analysis: Dict, today: date):
    """Applies adjustment rules based on recent performance."""
    day_to_check = today - timedelta(days=1) # Adjust based on yesterday's data
    if day_to_check not in historical_analysis: return
    
    analysis_today = historical_analysis[day_to_check]
    day_data = analysis_today.get("indicators", {})
    is_event = analysis_today["event"]

    # Rule: Do not adjust thresholds on days with symptoms
    symptoms_today = _define_event(historical_analysis.get(day_to_check, {}))
    if symptoms_today:
        for name, thresh in thresholds.items():
            thresh.false_alarm_count = 0
            thresh.event_at_ok_count = 0
            crud.upsert_indicator_threshold(db, thresh)
        return

    for ind_name, indicator in day_data.items():
        if ind_name == IndicatorName.FATIGUE_LOAD: continue
        
        thresh = thresholds.get(ind_name)
        if not thresh: continue
        
        # Reset counters if a month has passed since last reset
        if thresh.last_reset_date and (day_to_check - thresh.last_reset_date).days > ADJUSTMENT_PARAMS["lookback_days"]:
            thresh.false_alarm_count = 0
            thresh.event_at_ok_count = 0

        is_alert = indicator.label in [Label.CAUTION, Label.DANGER]
        
        if is_alert and not is_event:
            thresh.false_alarm_count += 1
        elif not is_alert and is_event:
            thresh.event_at_ok_count += 1
            
        # Apply adjustment rules
        reset_counts = False
        delta = ADJUSTMENT_PARAMS["deltas"].get(ind_name, 0)

        if thresh.false_alarm_count >= ADJUSTMENT_PARAMS["false_alarm_limit"]:
            thresh.caution_threshold += delta
            thresh.danger_threshold += delta
            reset_counts = True
            
        if thresh.event_at_ok_count >= ADJUSTMENT_PARAMS["event_at_ok_limit"]:
            thresh.caution_threshold -= delta
            thresh.danger_threshold -= delta
            reset_counts = True
            
        if reset_counts:
            thresh.false_alarm_count = 0
            thresh.event_at_ok_count = 0
            thresh.last_reset_date = day_to_check
        
        thresh.last_updated = datetime.now(timezone.utc)
        crud.upsert_indicator_threshold(db, thresh)
