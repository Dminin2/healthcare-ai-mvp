from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from datetime import date

from .. import schemas
from ..core import analysis_logic
from ..dependencies import get_db

router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
    responses={404: {"description": "Not found"}},
)

@router.get("/{date}", response_model=schemas.AnalysisResult, summary="Perform daily health risk analysis")
def get_daily_analysis(
    date: date = Path(..., description="The date for the analysis in YYYY-MM-DD format."),
    db_session: Session = Depends(get_db),
):
    """
    Performs a rule-based, explainable analysis of health risk for a given day.

    This endpoint orchestrates the data gathering, analysis, and formatting,
    by calling the core analysis logic.
    """
    analysis_result = analysis_logic.run_daily_analysis(
        db_session=db_session,
        analysis_date=date
    )
    
    # If the analysis returns nothing (e.g. due to major data fetching errors),
    # or if the result has critical missing fields, return a 404.
    if not analysis_result or (analysis_result.evidence and "Core data for today or yesterday" in analysis_result.evidence.missing_fields):
        raise HTTPException(status_code=404, detail="Insufficient data to perform analysis for the selected date. Core weather or health data may be missing for the target day or the day before.")
    
    return analysis_result
