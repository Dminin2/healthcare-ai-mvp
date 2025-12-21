import os
import json
from typing import Dict, Any, List

from ..prompts.daily_advice_prompt import ADVICE_PROMPT_TEMPLATE

# --- Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none").lower()
FIXED_CAUTION = "強い不調や不安がある場合は無理せず休み、必要に応じて医療機関へ相談してください。"

INDICATOR_MAP = {
    "high_temperature": "気温が高い",
    "low_temperature": "気温が低い",
    "precipitation": "降水量が多い",
    "temperature_change": "気温差が大きい",
    "high_activity": "活動量が多い",
    "sleep_deficit": "睡眠が短い",
    "elevated_resting_hr": "安静時心拍数が高め",
    "fatigue_load": "疲労が蓄積している可能性",
}

# --- Main Service Function ---

def generate_advice(analysis: Dict[str, Any]) -> str:
    """
    Generates a natural language health advice string from an analysis result.
    
    In Step 1, this function acts as a placeholder for a real LLM call.
    It reads the LLM_PROVIDER environment variable and, if it's 'none' or
    if any error occurs, it returns a hardcoded, rule-based fallback advice.
    """
    try:
        if LLM_PROVIDER == "none":
            return _generate_fallback_advice(analysis)
        else:
            # In Step 2, this branch will handle the actual LLM API call.
            # For now, it also returns the fallback as a safe default.
            # You would prepare the prompt and make the API call here.
            # prompt = ADVICE_PROMPT_TEMPLATE.format(analysis_json=json.dumps(analysis, indent=2, ensure_ascii=False))
            # advice = call_llm_api(prompt) 
            return _generate_fallback_advice(analysis)

    except Exception as e:
        # Failsafe: If any error occurs during generation, return the fallback.
        # This ensures the API never crashes due to LLM issues.
        print(f"Error during advice generation: {e}. Returning fallback.")
        # We pass an empty dict to the fallback to prevent further errors
        return _generate_fallback_advice(analysis or {})

# --- Fallback Logic Implementation ---

def _normalize_label(label: Any) -> int:
    """Converts 'ok'/'caution'/'danger' or other formats to 0, 1, 2."""
    if isinstance(label, int):
        return label
    if isinstance(label, str):
        label_lower = label.lower()
        if label_lower == "danger": return 2
        if label_lower == "caution": return 1
    return 0

def _generate_fallback_advice(analysis: Dict[str, Any]) -> str:
    """
    Generates a rule-based, Japanese advice string as a fallback.
    """
    if not analysis:
        return f"解析データがありません。\n\n【メモ】\n{FIXED_CAUTION}"

    overall_level = analysis.get("overall_level", "ok")
    
    # 1. Generate the header
    header = ""
    if overall_level == "danger":
        header = "今日は体調リスクが高めです。無理は控え、慎重に過ごしましょう。"
    elif overall_level == "caution":
        header = "今日は体調に注意が必要そうです。ご自身のペースを大切にしてください。"
    else:
        header = "今日の全体的な体調リスクは低めです。引き続き良い状態を維持しましょう。"

    # 2. Filter and sort indicators
    indicators = analysis.get("indicators", [])
    
    alert_indicators = []
    for ind in indicators:
        # Normalize label and add to indicator dict
        ind['normalized_label'] = _normalize_label(ind.get("label"))
        if ind['normalized_label'] > 0:
            alert_indicators.append(ind)
            
    # Sort by danger first, then caution
    alert_indicators.sort(key=lambda x: x['normalized_label'], reverse=True)
    
    # 3. Build the points list
    points_lines = []
    for ind in alert_indicators[:3]: # Max 3 points
        name = ind.get("name", "不明な指標")
        jp_name = INDICATOR_MAP.get(name, name)
        level_text = "警戒" if ind['normalized_label'] == 2 else "注意"
        
        line = f"- {jp_name}（{level_text}レベル）"
        
        value = ind.get("value")
        unit = ind.get("unit")
        if value is not None and unit:
             line += f": {value}{unit}"

        symptoms = ind.get("related_symptoms", [])
        if symptoms:
            symptoms_text = "、".join(symptoms[:2])
            line += f"。起きやすい自覚症状は「{symptoms_text}」です。"
        
        points_lines.append(line)

    # 4. Combine all parts
    if points_lines:
        points_section = "【注意ポイント】\n" + "\n".join(points_lines)
        advice = f"【総合】\n{header}\n\n{points_section}\n\n【メモ】\n{FIXED_CAUTION}"
    else:
        # If no alerts, the header is sufficient
        advice = f"【総合】\n{header}\n\n【注意ポイント】\n特に注意が必要な点はありませんでした。\n\n【メモ】\n{FIXED_CAUTION}"

    return advice
