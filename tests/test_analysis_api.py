import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# No need to import local fixtures; pytest will find fixtures in conftest.py
# The fixtures are implicitly available from conftest.py

from app.core import analysis_logic # Needed for INITIAL_THRESHOLDS
from app import models # Added this import

# --- Test Cases ---

@pytest.mark.test_db_url("sqlite:///./test_analysis.db")
def test_thresholds_are_initialized(db_session_for_test_function, test_user):
    count_before = db_session_for_test_function.query(models.IndicatorThreshold).count()
    assert count_before == 0

    analysis_logic._initialize_thresholds(db_session_for_test_function, test_user.id)

    count_after = db_session_for_test_function.query(models.IndicatorThreshold).count()
    assert count_after == len(analysis_logic.INITIAL_THRESHOLDS)


@pytest.mark.test_db_url("sqlite:///./test_analysis.db")
def test_analysis_with_populated_data(test_client, populate_generic_test_data):
    analysis_date = populate_generic_test_data
    response = test_client.get(f"/analysis/{analysis_date.isoformat()}")
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["date"] == analysis_date.isoformat()
    assert result["total_points"] == 4
    assert result["overall_level"] == "danger"
    
    indicators = {ind["name"]: ind for ind in result["indicators"]}
    assert indicators["sleep_deficit"]["label"] == "danger"
    assert indicators["sleep_deficit"]["value"] == 4.5
    assert indicators["temperature_change"]["label"] == "danger"
    assert indicators["temperature_change"]["value"] == 14.0
    
    assert "high_temperature" in result["event_rates"]
    assert "fatigue" in indicators["high_temperature"]["related_symptoms"]

@pytest.mark.test_db_url("sqlite:///./test_analysis.db")
def test_analysis_insufficient_data(test_client):
    response = test_client.get("/analysis/2030-01-01")
    assert response.status_code == 404
    assert "Insufficient data" in response.json()["detail"]
