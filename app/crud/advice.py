from sqlalchemy.orm import Session
from datetime import date, datetime, timezone
from typing import Optional

from .. import models # app/models をインポート
from .. import schemas # app/schemas をインポート

def get_daily_advice_by_date(db: Session, target_date: date) -> Optional[models.DailyAdvice]:
    """
    指定された日付のアドバイス結果をデータベースから取得します。
    """
    return db.query(models.DailyAdvice).filter(models.DailyAdvice.date == target_date).first()

def create_advice(
    db: Session,
    advice_date: date,
    overall_level: str,
    total_points: int,
    advice_text: str,
    source: str
) -> models.DailyAdvice:
    """
    新しいアドバイス結果をデータベースに保存します。
    既存のアドバイスがある場合は更新します (upsert)。
    """
    db_obj = get_daily_advice_by_date(db, advice_date)

    if db_obj:
        # Update existing record
        db_obj.overall_level = overall_level
        db_obj.total_points = total_points
        db_obj.advice_text = advice_text
        db_obj.source = source
        # created_at は更新しない
    else:
        # Create new record
        db_obj = models.DailyAdvice(
            date=advice_date,
            overall_level=overall_level,
            total_points=total_points,
            advice_text=advice_text,
            source=source,
            created_at=datetime.now(timezone.utc)
        )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
