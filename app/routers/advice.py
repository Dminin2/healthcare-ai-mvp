from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from datetime import date

from .. import crud, schemas, models
from ..core import analysis_logic
from ..services import llm_client
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/advice",
    tags=["Advice"],
    responses={404: {"description": "not found"}},
)


@router.get("/{date}", response_model=schemas.AdviceResponse,
            summary="Generate natural language health advice")
def get_daily_advice(
    date: date = Path(..., description="The date for the advice in YYYY-MM-DD format."),
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = current_user.id

    # 1. Return cached advice if available
    stored = crud.get_daily_advice_by_date(db_session, user_id, date)
    if stored:
        return schemas.AdviceResponse(
            date=stored.date,
            overall_level=stored.overall_level,
            total_points=stored.total_points,
            advice=stored.advice_text,
        )

    # 2. Run analysis
    analysis_result = analysis_logic.run_daily_analysis(
        db_session=db_session, analysis_date=date, user_id=user_id
    )

    has_missing = (
        analysis_result
        and analysis_result.evidence
        and any("Core data" in f for f in analysis_result.evidence.missing_fields)
    )
    if not analysis_result or has_missing:
        raise HTTPException(
            status_code=404,
            detail="分析に必要なデータが不足しているため、アドバイスを生成できません。",
        )

    # 3. Generate natural language advice
    generated_text, advice_source = llm_client.generate_advice(
        analysis_result.model_dump(mode="json")
    )

    # 4. Persist generated advice
    crud.upsert_daily_advice(
        db_session,
        user_id,
        schemas.DailyAdviceCreate(
            date=analysis_result.date,
            overall_level=analysis_result.overall_level,
            total_points=analysis_result.total_points,
            advice_text=generated_text,
            source=advice_source,
        ),
    )

    return schemas.AdviceResponse(
        date=analysis_result.date,
        overall_level=analysis_result.overall_level,
        total_points=analysis_result.total_points,
        advice=generated_text,
    )
