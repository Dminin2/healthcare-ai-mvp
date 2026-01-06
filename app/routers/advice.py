from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from datetime import date
# from pydantic import BaseModel # Removed, now defined in schemas

from .. import crud, schemas # Import crud and schemas
from ..core import analysis_logic
from ..services import llm_client
from ..dependencies import get_db

# --- Response Schema ---
# class AdviceResponse(BaseModel): # Removed, now defined in schemas
#     date: date
#     overall_level: str
#     total_points: int
#     advice: str

# --- Router Definition ---
router = APIRouter(
    prefix="/advice",
    tags=["Advice"],
    responses={404: {"description": "not found"}},
)

@router.get("/{date}", response_model=schemas.AdviceResponse, summary="Generate natural language health advice")
def get_daily_advice(
    date: date = Path(..., description="The date for the advice in YYYY-MM-DD format."),
    db_session: Session = Depends(get_db),
):
    """
    Retrieves the daily analysis result and formats it into a natural
    language advice string using the LLM service (or its fallback).
    First checks DB for saved advice for the day.
    """
    # 1. Check DB for existing advice
    stored_advice_record = crud.get_daily_advice_by_date(db_session, date)
    if stored_advice_record:
        # If advice found, return it
        return schemas.AdviceResponse(
            date=stored_advice_record.date,
            overall_level=stored_advice_record.overall_level,
            total_points=stored_advice_record.total_points,
            advice=stored_advice_record.advice_text # Use advice_text from DB
        )

    # 2. If no advice in DB, proceed with analysis and generation
    analysis_result = analysis_logic.run_daily_analysis(
        db_session=db_session,
        analysis_date=date
    )

    has_missing_data = False
    if analysis_result and analysis_result.evidence:
        has_missing_data = any("Core data" in field for field in analysis_result.evidence.missing_fields)

    if not analysis_result or has_missing_data:
        raise HTTPException(
            status_code=404,
            detail="分析に必要なデータが不足しているため、アドバイスを生成できません。"
        )

    # 3. Pass the dictionary to the LLM client to get the advice string and source
    # llm_client.generate_advice now returns a tuple (advice_string, source_name)
    generated_advice_string, advice_source = llm_client.generate_advice(analysis_result.model_dump(mode='json'))

    # 4. Save the newly generated advice to DB
    new_advice = schemas.DailyAdviceCreate(
        date=analysis_result.date,
        overall_level=analysis_result.overall_level,
        total_points=analysis_result.total_points,
        advice_text=generated_advice_string, # Use advice_text
        source=advice_source # Save the source
    )
    crud.upsert_daily_advice(db_session, new_advice)


    # 5. Construct the final API response.
    return schemas.AdviceResponse(
        date=analysis_result.date,
        overall_level=analysis_result.overall_level,
        total_points=analysis_result.total_points,
        advice=generated_advice_string # Still named 'advice' for API compatibility
    )
