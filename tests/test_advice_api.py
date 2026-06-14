import pytest
from datetime import date
import os
import app.services.llm_client as llm_module


# --- Test Cases ---

@pytest.mark.test_db_url("sqlite:///./test_advice.db")
def test_get_advice_with_sufficient_data(test_client, populate_generic_test_data, monkeypatch):
    """Tests GET /advice/{date} with sufficient data and LLM disabled (fallback mode)."""
    analysis_date = populate_generic_test_data

    # Force fallback (module-level constant must be patched directly)
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "none")

    response = test_client.get(f"/advice/{analysis_date.isoformat()}")
    assert response.status_code == 200
    data = response.json()

    assert "date" in data and "overall_level" in data and "advice" in data
    assert data["date"] == analysis_date.isoformat()
    assert data["overall_level"] == "danger"

    advice = data["advice"]
    assert isinstance(advice, str) and len(advice) > 50
    assert "【総合】" in advice and "【注意ポイント】" in advice and "【メモ】" in advice
    assert "睡眠が短い" in advice
    assert "気温" in advice


@pytest.mark.test_db_url("sqlite:///./test_advice.db")
def test_get_advice_with_insufficient_data(test_client):
    """Tests that /advice returns 404 when analysis data is missing."""
    response = test_client.get("/advice/2030-01-01")
    assert response.status_code == 404
    assert "Insufficient data to generate advice" in response.json()["detail"]


@pytest.mark.test_db_url("sqlite:///./test_advice.db")
def test_get_advice_llm_api_key_missing_fallback(test_client, populate_generic_test_data, monkeypatch):
    """Tests that the system falls back to rule-based advice when LLM is disabled."""
    analysis_date = populate_generic_test_data

    # Force fallback regardless of env vars
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "none")

    response = test_client.get(f"/advice/{analysis_date.isoformat()}")
    assert response.status_code == 200
    data = response.json()

    assert "date" in data and "overall_level" in data and "advice" in data
    assert data["overall_level"] == "danger"
    assert "【総合】" in data["advice"]
    assert "【注意ポイント】" in data["advice"]
    assert "【メモ】" in data["advice"]
    assert "睡眠が短い" in data["advice"]
    assert "気温" in data["advice"]
