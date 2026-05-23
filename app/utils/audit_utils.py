from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User
from app.enums import AuditAction
from typing import Optional, Dict, Any
import json


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log an action to the audit trail."""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(audit_log)
        self.db.commit()

        return audit_log

    def log_user_action(
        self,
        user: User,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request_info: Optional[Dict[str, str]] = None,
    ) -> AuditLog:
        """Log a user action with request information."""
        ip_address = request_info.get("ip_address") if request_info else None
        user_agent = request_info.get("user_agent") if request_info else None

        return self.log_action(
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs with optional filters."""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)

        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)

        if action:
            query = query.filter(AuditLog.action == action)

        return (
            query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        )

    def get_user_activity_summary(self, user_id: int, days: int = 30) -> Dict[str, int]:
        """Get activity summary for a user."""
        from datetime import datetime, timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        logs = (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id, AuditLog.created_at >= start_date)
            .all()
        )

        summary = {}
        for log in logs:
            summary[log.action] = summary.get(log.action, 0) + 1

        return summary


def create_audit_logger(db: Session) -> AuditService:
    """Create audit service instance."""
    return AuditService(db)
