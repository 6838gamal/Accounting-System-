"""
خدمة سجل العمليات
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog


class ActivityService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        user_id: Optional[int],
        action: str,
        module: str,
        record_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> ActivityLog:
        """تسجيل عملية جديدة"""
        log = ActivityLog(
            user_id=user_id,
            action=action,
            module=module,
            record_id=record_id,
            details=details,
            ip_address=ip_address,
        )
        self.db.add(log)
        self.db.commit()
        return log

    def get_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        module: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        query = self.db.query(ActivityLog)
        if module:
            query = query.filter(ActivityLog.module == module)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        total = query.count()
        logs = query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit).all()
        return logs, total
