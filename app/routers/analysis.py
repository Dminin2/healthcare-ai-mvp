from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from .. import schemas, models
from ..core import analysis_logic
from ..dependencies import get_db, get_current_admin

router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{date}", response_model=schemas.AnalysisResult,
            summary="Perform daily health risk analysis (管理者専用)")
def get_daily_analysis(
    date: date = Path(..., description="The date for the analysis in YYYY-MM-DD format."),
    user_id: Optional[int] = Query(None, description="対象ユーザーID（省略時は管理者自身）"),
    db_session: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    """
    指定ユーザーの日次健康リスク分析を実行します。管理者のみ実行可能です。
    user_id を省略した場合は管理者自身のデータを分析します。
    """
    target_user_id = user_id if user_id is not None else current_admin.id

    analysis_result = analysis_logic.run_daily_analysis(
        db_session=db_session, analysis_date=date, user_id=target_user_id
    )

    if not analysis_result or (
        analysis_result.evidence
        and "Core data for today or yesterday" in analysis_result.evidence.missing_fields
    ):
        raise HTTPException(
            status_code=404,
            detail="Insufficient data to perform analysis for the selected date. "
                   "Core weather or health data may be missing for the target day or the day before.",
        )

    return analysis_result
