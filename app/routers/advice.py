from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel

from ..core import analysis_logic
from ..services import llm_client
from ..dependencies import get_db

# --- Response Schema ---
class AdviceResponse(BaseModel):
    date: date
    overall_level: str
    total_points: int
    advice: str

# --- Router Definition ---
router = APIRouter(
    prefix="/advice",
    tags=["Advice"],
    responses={404: {"description": "Not found"}},
)

@router.get("/{date}", response_model=AdviceResponse, summary="Generate natural language health advice")
def get_daily_advice(
    date: date = Path(..., description="The date for the advice in YYYY-MM-DD format."),
    db_session: Session = Depends(get_db),
):
    """
    Retrieves the daily analysis result and formats it into a natural
    language advice string using the LLM service (or its fallback).
    """
    # 1. Call the existing analysis logic directly to get the structured result.
    # This avoids an internal HTTP call and is more efficient.
    analysis_result = analysis_logic.run_daily_analysis(
        db_session=db_session,
        analysis_date=date
    )
    
    if not analysis_result or (analysis_result.evidence and "Core data for today or yesterday" in analysis_result.evidence.missing_fields):
        raise HTTPException(
            status_code=404,
            detail="Insufficient data to perform analysis, so advice cannot be generated."
        )

    # 2. Convert the Pydantic model to a dictionary.
    analysis_dict = analysis_result.model_dump(mode='json')

    # 3. Pass the dictionary to the LLM client to get the advice string.
    advice_string = llm_client.generate_advice(analysis_dict)

    # 4. Construct the final API response.
    return AdviceResponse(
        date=analysis_result.date,
        overall_level=analysis_result.overall_level,
        total_points=analysis_result.total_points,
        advice=advice_string
    )
