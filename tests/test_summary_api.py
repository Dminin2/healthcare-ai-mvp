import pytest
from datetime import datetime, date, timezone, timedelta

# No need to import local fixtures; pytest will find fixtures in conftest.py
# The fixtures are implicitly available from conftest.py

from app import models # Import models to directly manipulate data in tests
from app import schemas # Import schemas for type checking responses

# --- Test Cases for GET /summary/last7d ---

@pytest.mark.test_db_url("sqlite:///./test_summary.db")
def test_summary_last7d_empty_data(test_client):
    """Test /summary/last7d with no data inserted."""
    response = test_client.get("/summary/last7d")
    assert response.status_code == 200
    summary_data = response.json()
    assert len(summary_data) == 7
    for day in summary_data:
        assert day["weather"] is None
        assert day["daily_state"] is None
        assert day["health_metrics"] is None

@pytest.mark.test_db_url("sqlite:///./test_summary.db")
def test_summary_last7d_with_complete_data(test_client, db_session_for_test_function):
    """Test /summary/last7d with data for all categories on a specific day."""
    yesterday_utc_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    
    db_session_for_test_function.add(models.Weather(date=yesterday_utc_date, temp_max=25.0, temp_min=15.0, precipitation_sum=5.0))
    db_session_for_test_function.add(models.DailyState(date=yesterday_utc_date, mood=4, symptoms=["headache"], notes="Feeling okay"))
    db_session_for_test_function.add(models.StepCount(timestamp=datetime.combine(yesterday_utc_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=8), value=5000))
    db_session_for_test_function.add(models.StepCount(timestamp=datetime.combine(yesterday_utc_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=18), value=2500))
    db_session_for_test_function.add(models.RestingHeartRate(timestamp=datetime.combine(yesterday_utc_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6), value=60))
    db_session_for_test_function.add(models.SleepSession(session_end_time=datetime.combine(yesterday_utc_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6), total_sleep_hours=7.5, created_at=datetime.now(timezone.utc), session_start_time=datetime.now(timezone.utc)))
    db_session_for_test_function.commit()

    response = test_client.get("/summary/last7d")
    assert response.status_code == 200
    summary_data = response.json()
    
    yesterday_summary = next((d for d in summary_data if d["date"] == yesterday_utc_date.isoformat()), None)
    assert yesterday_summary is not None
    assert yesterday_summary["weather"]["temp_max"] == 25.0
    assert yesterday_summary["daily_state"]["mood"] == 4
    assert yesterday_summary["health_metrics"]["steps"] == 7500
    assert yesterday_summary["health_metrics"]["resting_hr"] == 60.0
    assert yesterday_summary["health_metrics"]["sleep_hours"] == 7.5
