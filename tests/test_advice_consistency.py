"""
Tests that verify the natural-language advice output is consistent with metric values.

Covers:
  - Secondary display guards in _generate_fallback_advice()
  - Hard bounds in _apply_threshold_bounds()
"""
import pytest
from app.services.llm_client import _generate_fallback_advice
from app.core.analysis_logic import _apply_threshold_bounds, IndicatorName
from app import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ind(name, label, value, unit=None, symptoms=None):
    return {"name": name, "label": label, "value": value, "unit": unit, "related_symptoms": symptoms or []}


def _analysis(indicators, overall_level="caution", total_points=1):
    return {
        "date": "2026-04-21",
        "overall_level": overall_level,
        "total_points": total_points,
        "indicators": indicators,
    }


# ---------------------------------------------------------------------------
# Display guard tests
# ---------------------------------------------------------------------------

def test_precipitation_zero_not_shown_as_high():
    """0.0mm marked CAUTION must not produce '降水量が多い' in advice."""
    advice = _generate_fallback_advice(_analysis([_ind("precipitation", "caution", 0.0, "mm")]))
    assert "降水量が多い" not in advice


def test_elevated_rhr_sub_one_delta_not_shown():
    """0.67 bpm delta (below 1.0 guard) must not produce '安静時心拍数が高め' in advice."""
    advice = _generate_fallback_advice(_analysis([_ind("elevated_resting_hr", "caution", 0.67, "bpm")]))
    assert "安静時心拍数が高め" not in advice


def test_sleep_deficit_shown_for_short_sleep():
    """6.38h sleep marked CAUTION must appear as '睡眠が短い' in advice."""
    advice = _generate_fallback_advice(_analysis([_ind("sleep_deficit", "caution", 6.38, "h")]))
    assert "睡眠が短い" in advice


def test_all_ok_indicators_produce_no_alert_points():
    """All-OK indicators must result in the 'no alerts' message."""
    advice = _generate_fallback_advice(_analysis(
        [
            _ind("precipitation", "ok", 1.5, "mm"),
            _ind("elevated_resting_hr", "ok", 2.0, "bpm"),
            _ind("sleep_deficit", "ok", 7.5, "h"),
        ],
        overall_level="ok",
        total_points=0,
    ))
    assert "特に注意が必要な点はありません" in advice


def test_mixed_valid_and_invalid_alerts_only_valid_shown():
    """Invalid-guard indicators are suppressed; valid ones still appear."""
    advice = _generate_fallback_advice(_analysis([
        _ind("precipitation", "caution", 0.0, "mm"),         # invalid: 0.0mm
        _ind("elevated_resting_hr", "caution", 0.5, "bpm"),  # invalid: < 1.0 bpm
        _ind("sleep_deficit", "caution", 5.5, "h"),          # valid
    ]))
    assert "降水量が多い" not in advice
    assert "安静時心拍数が高め" not in advice
    assert "睡眠が短い" in advice


def test_none_value_indicator_skipped_and_no_crash():
    """None-value indicators must be skipped silently."""
    advice = _generate_fallback_advice(_analysis([_ind("elevated_resting_hr", "caution", None, "bpm")]))
    assert isinstance(advice, str)
    assert "安静時心拍数が高め" not in advice


def test_display_value_rounded_to_one_decimal():
    """Displayed metric values must be rounded to 1 decimal place."""
    advice = _generate_fallback_advice(_analysis([_ind("sleep_deficit", "caution", 6.38, "h")]))
    assert "6.4h" in advice
    assert "6.38h" not in advice


# ---------------------------------------------------------------------------
# Threshold bounds tests
# ---------------------------------------------------------------------------

def _make_thresh(name, caution, danger):
    return models.IndicatorThreshold(
        indicator_name=name,
        caution_threshold=caution,
        danger_threshold=danger,
    )


def test_precipitation_caution_threshold_clamped_above_one():
    """Drifted precipitation caution threshold must be raised to >= 1.0mm."""
    thresh = _make_thresh(IndicatorName.PRECIPITATION, caution=0.0, danger=5.0)
    _apply_threshold_bounds(thresh, IndicatorName.PRECIPITATION)
    assert thresh.caution_threshold >= 1.0


def test_precipitation_danger_threshold_clamped_above_eight():
    """Drifted precipitation danger threshold must be raised to >= 8.0mm."""
    thresh = _make_thresh(IndicatorName.PRECIPITATION, caution=2.0, danger=1.0)
    _apply_threshold_bounds(thresh, IndicatorName.PRECIPITATION)
    assert thresh.danger_threshold >= 8.0


def test_elevated_rhr_caution_threshold_clamped_above_one():
    """Drifted elevated_resting_hr caution threshold must be raised to >= 1.0 bpm."""
    thresh = _make_thresh(IndicatorName.ELEVATED_RESTING_HR, caution=0.5, danger=2.0)
    _apply_threshold_bounds(thresh, IndicatorName.ELEVATED_RESTING_HR)
    assert thresh.caution_threshold >= 1.0


def test_sleep_deficit_threshold_clamped_within_range():
    """Drifted sleep_deficit thresholds must stay within [4.0, 8.0] / [3.0, 6.5]."""
    thresh = _make_thresh(IndicatorName.SLEEP_DEFICIT, caution=9.0, danger=7.0)
    _apply_threshold_bounds(thresh, IndicatorName.SLEEP_DEFICIT)
    assert thresh.caution_threshold <= 8.0
    assert thresh.danger_threshold <= 6.5

    thresh2 = _make_thresh(IndicatorName.SLEEP_DEFICIT, caution=2.0, danger=1.0)
    _apply_threshold_bounds(thresh2, IndicatorName.SLEEP_DEFICIT)
    assert thresh2.caution_threshold >= 4.0
    assert thresh2.danger_threshold >= 3.0


def test_bounds_not_applied_to_unknown_indicator():
    """Indicators without defined bounds must pass through unchanged."""
    thresh = _make_thresh("unknown_indicator", caution=-999.0, danger=-999.0)
    _apply_threshold_bounds(thresh, "unknown_indicator")
    assert thresh.caution_threshold == -999.0
    assert thresh.danger_threshold == -999.0
