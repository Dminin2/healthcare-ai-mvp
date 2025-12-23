import pytest
from datetime import datetime, timezone
import os

# No need to import local fixtures; pytest will find fixtures in conftest.py
# The fixtures are implicitly available from conftest.py

# Import models for database assertions
from app import models # Add this import

# --- Test Data Payloads ---
def get_valid_payload():
    time = datetime.now(timezone.utc).isoformat()
    return {"data": {"metrics": [
        {"name": "step_count", "units": "count", "data": [{"date": time, "qty": 500}]},
        {"name": "sleep_analysis", "data": [{"date": "2025-12-19", "sleepStart": "2025-12-19T22:00:00Z", "sleepEnd": "2025-12-20T06:00:00Z", "totalSleep": 8}]}
    ]}}

def get_invalid_qty_payload():
    time = datetime.now(timezone.utc).isoformat()
    return {"data": {"metrics": [
        {"name": "resting_heart_rate", "units": "bpm", "data": [{"date": time, "qty": "invalid"}]}
    ]}}

# --- Test Cases ---
@pytest.mark.test_db_url("sqlite:///./test_ingestion.db")
def test_ingest_health_metrics_success(test_client, db_session_for_test_function):
    response = test_client.post("/ingest/health_metrics", json=get_valid_payload())
    assert response.status_code == 200
    summary = response.json()
    assert summary["records_inserted"] == 2
    assert db_session_for_test_function.query(models.StepCount).count() == 1
    assert db_session_for_test_function.query(models.SleepSession).count() == 1

@pytest.mark.test_db_url("sqlite:///./test_ingestion.db")
def test_ingest_health_metrics_with_warnings_and_skips(test_client, db_session_for_test_function):
    response = test_client.post("/ingest/health_metrics", json=get_invalid_qty_payload())
    assert response.status_code == 200
    summary = response.json()
    assert summary["records_skipped"] == 1
    assert len(summary["warnings"]) > 0
    assert db_session_for_test_function.query(models.RestingHeartRate).count() == 0

@pytest.mark.test_db_url("sqlite:///./test_ingestion.db")
def test_bad_payload_structure(test_client):
    response = test_client.post("/ingest/health_metrics", json={"wrong_key": "value"})
    assert response.status_code == 422