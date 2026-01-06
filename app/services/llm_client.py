import os
import logging
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

logger = logging.getLogger(__name__)

from ..prompts.daily_advice_prompt import ADVICE_PROMPT_TEMPLATE

# --- Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
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

# def generate_advice(analysis: Dict[str, Any]) -> str:
#     """
#     Generates a natural language health advice string from an analysis result.

#     In Step 1, this function acts as a placeholder for a real LLM call.
#     It reads the LLM_PROVIDER environment variable and, if it's 'none' or
#     if any error occurs, it returns a hardcoded, rule-based fallback advice.
#     """
#     try:
#         # LLM_PROVIDERがgeminiで、かつAPIキーがある場合のみGeminiを実行
#         if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
#             advice_text = _generate_gemini_advice(analysis)
#             if advice_text:
#                 return advice_text

#         # それ以外（none設定やAPIエラー時）はフォールバックを返す
#         return _generate_fallback_advice(analysis)

#     except Exception as e:
#         logger.error(f"Error during advice generation: {e}")
#         return _generate_fallback_advice(analysis or {})

def generate_advice(analysis: Dict[str, Any]) -> tuple[str, str]: # 返り値をタプルに変更
    try:
        if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
            advice_text = _generate_gemini_advice(analysis)
            if advice_text:
                return advice_text, "gemini" # ソースを返す

        return _generate_fallback_advice(analysis), "fallback" # ソースを返す

    except Exception as e:
        logger.error(f"Error during advice generation: {e}")
        return _generate_fallback_advice(analysis or {}), "error_fallback"

def _generate_gemini_advice(analysis: Dict[str, Any]) -> Optional[str]:
    """Gemini APIを使用して文章を生成する内部関数"""
    try:
        from google import genai

        # 入力データの整形（安全のため必要最小限にする）
        minimal_analysis = {
            "date": analysis.get("date"),
            "overall_level": analysis.get("overall_level"),
            "total_points": analysis.get("total_points"),
            "indicators": [
                {k: v for k, v in ind.items() if k in ["name", "label", "value", "unit", "related_symptoms"]}
                for ind in analysis.get("indicators", [])
            ]
        }

        prompt = ADVICE_PROMPT_TEMPLATE.format(
            analysis_json=json.dumps(minimal_analysis, ensure_ascii=False)
        )

        client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options={"api_version": "v1"},
        )

        for m in client.models.list():
            print(m.name)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if not response or not response.text:
            return None

        text = response.text.strip()

        # ガード：空文字または2000文字超なら無効
        if len(text) == 0 or len(text) > 2000:
            return None

        return text

    except Exception as e:
        logger.error(f"Gemini API invocation failed: {e}")
        return None

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
