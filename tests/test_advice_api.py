import pytest
from datetime import date
import os

# --- Test Cases ---

@pytest.mark.test_db_url("sqlite:///./test_advice.db")
def test_get_advice_with_sufficient_data(test_client, populate_generic_test_data):
    """
    Tests the GET /advice/{date} endpoint with enough data.
    Ensures that even with the LLM provider disabled, it returns a valid
    fallback advice string.
    """
    analysis_date = populate_generic_test_data # populate_generic_test_data returns the date
    # Ensure LLM_PROVIDER is "none" for this test (default in client, set in conftest test_client)
    response = test_client.get(f"/advice/{analysis_date.isoformat()}")

    assert response.status_code == 200
    data = response.json()

    assert "date" in data and "overall_level" in data and "advice" in data
    assert data["date"] == analysis_date.isoformat()
    assert data["overall_level"] == "danger"

    advice = data["advice"]
    assert isinstance(advice, str) and len(advice) > 50
    assert "【総合】" in advice and "【注意ポイント】" in advice and "【メモ】" in advice
    # Fallback message includes these indicators for the populated data
    assert "睡眠不足" in advice
    assert "気温" in advice

@pytest.mark.test_db_url("sqlite:///./test_advice.db")
def test_get_advice_with_insufficient_data(test_client):
    """
    Tests that the /advice endpoint returns a 404 if the underlying
    analysis cannot be performed due to missing data.
    """
    # No data populated for this specific test
    response = test_client.get("/advice/2030-01-01")
    assert response.status_code == 404
    assert "分析に必要なデータが不足しているため、アドバイスを生成できません。" in response.json()["detail"]


@pytest.mark.test_db_url("sqlite:///./test_advice.db")
def test_get_advice_llm_api_key_missing_fallback(test_client, populate_generic_test_data, monkeypatch):
    """
    Tests that if LLM_PROVIDER is "gemini" but GEMINI_API_KEY is missing,
    the system falls back to rule-based advice.
    """
    analysis_date = populate_generic_test_data

    # Set LLM_PROVIDER to "gemini" but ensure GEMINI_API_KEY is not set
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False) # Ensure it's not set

    response = test_client.get(f"/advice/{analysis_date.isoformat()}")

    assert response.status_code == 200
    data = response.json()

    assert "date" in data and "overall_level" in data and "advice" in data
    assert data["overall_level"] == "danger" # Based on populated data

    # Assert that the advice is the rule-based fallback
    assert "【総合】" in data["advice"]
    assert "【注意ポイント】" in data["advice"]
    assert "【メモ】" in data["advice"]
    assert "睡眠不足" in data["advice"]
    assert "気温" in data["advice"]
