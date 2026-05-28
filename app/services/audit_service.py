"""
Audit Service for Mediflow System

This service handles audit logging and compliance tracking including:
- Comprehensive activity logging
- Compliance reporting
- Security monitoring
- Audit trail management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from app.models.audit_log import AuditLog
from app.models.user import User
from app.enums import AuditAction
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def create_audit_logger(db: Session) -> logging.LoggerAdapter:
    """
    Create a logger adapter for audit logging.

    Args:
        db: Database session

    Returns:
        Logger adapter with audit context
    """

    class AuditLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # Add audit context to log messages
            audit_context = kwargs.pop("audit_context", {})
            if audit_context:
                msg = f"[AUDIT] {msg} | Context: {audit_context}"
            return msg, kwargs

        def log_action(
            self,
            user_id: int,
            action: str,
            entity_type: str,
            entity_id: Optional[int] = None,
            details: Optional[Dict[str, Any]] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
        ):
            """Log audit action directly through logger."""
            audit_service = AuditService(db)
            audit_service.log_action(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )

    # Create base logger
    audit_logger = logging.getLogger("mediflow.audit")
    audit_logger.setLevel(logging.INFO)

    # Create adapter
    return AuditLoggerAdapter(audit_logger, {})


class AuditService:
    """Service for audit and compliance operations."""

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
        """
        Log an action to the audit trail.

        Args:
            user_id: ID of user performing action
            action: Action performed
            entity_type: Type of entity affected
            entity_id: ID of entity affected
            details: Additional details about action
            ip_address: IP address of user
            user_agent: User agent string

        Returns:
            Created audit log entry
        """
        import json

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get audit logs with optional filters.

        Args:
            user_id: Optional user ID filter
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter
            action: Optional action filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        query = self.db.query(AuditLog)

        # Apply filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)

        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)

        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

    def get_user_activity_summary(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get activity summary for a specific user.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Dictionary with user activity summary
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get user's audit logs
        logs = (
            self.db.query(AuditLog)
            .filter(
                and_(AuditLog.user_id == user_id, AuditLog.created_at >= start_date)
            )
            .all()
        )

        # Action breakdown
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        # Entity type breakdown
        entity_counts = {}
        for log in logs:
            entity_counts[log.entity_type] = entity_counts.get(log.entity_type, 0) + 1

        # Daily activity
        daily_activity = {}
        for log in logs:
            day = log.created_at.date().isoformat()
            daily_activity[day] = daily_activity.get(day, 0) + 1

        # Most recent activity
        recent_logs = sorted(logs, key=lambda x: x.created_at, reverse=True)[:10]

        return {
            "period_days": days,
            "total_actions": len(logs),
            "action_breakdown": action_counts,
            "entity_breakdown": entity_counts,
            "daily_activity": daily_activity,
            "recent_activity": [
                {
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "created_at": log.created_at,
                    "ip_address": log.ip_address,
                }
                for log in recent_logs
            ],
        }

    def get_entity_history(
        self, entity_type: str, entity_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get complete history for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity

        Returns:
            List of historical actions
        """
        logs = (
            self.db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
                )
            )
            .order_by(desc(AuditLog.created_at))
            .all()
        )

        # Enrich with user information
        user_ids = {log.user_id for log in logs}
        users = {
            user.id: user
            for user in self.db.query(User).filter(User.id.in_(user_ids)).all()
        }

        return [
            {
                "id": log.id,
                "action": log.action,
                "user": {
                    "id": users[log.user_id].id,
                    "name": f"{users[log.user_id].first_name} {users[log.user_id].last_name}",
                    "role": users[log.user_id].role,
                }
                if log.user_id in users
                else None,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at,
            }
            for log in logs
        ]

    def get_compliance_report(
        self, facility_id: Optional[int] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit purposes.

        Args:
            facility_id: Optional facility ID filter
            days: Number of days to analyze

        Returns:
            Dictionary with compliance metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Base query for audit logs
        query = self.db.query(AuditLog).filter(AuditLog.created_at >= start_date)

        # Filter by facility if specified
        if facility_id:
            # Get users from this facility
            facility_user_ids = (
                self.db.query(User.id)
                .filter(User.facility_id == facility_id)
                .subquery()
            )
            query = query.filter(AuditLog.user_id.in_(facility_user_ids))

        # Get all logs
        logs = query.all()

        # Security metrics
        login_logs = [log for log in logs if log.action == AuditAction.LOGIN.value]
        failed_logins = [log for log in logs if log.action == "login_failed"]
        user_creation_logs = [
            log
            for log in logs
            if log.action == AuditAction.CREATE.value and log.entity_type == "user"
        ]

        # Data access metrics
        patient_access_logs = [log for log in logs if log.entity_type == "patient"]
        referral_access_logs = [log for log in logs if log.entity_type == "referral"]

        # Data modification metrics
        create_logs = [log for log in logs if log.action == AuditAction.CREATE.value]
        update_logs = [log for log in logs if log.action == AuditAction.UPDATE.value]
        delete_logs = [log for log in logs if log.action == AuditAction.DELETE.value]

        # File operations
        upload_logs = [log for log in logs if log.action == AuditAction.UPLOAD.value]
        download_logs = [
            log for log in logs if log.action == AuditAction.DOWNLOAD.value
        ]

        # Unique users
        unique_users = len({log.user_id for log in logs})

        # IP address analysis
        unique_ips = len({log.ip_address for log in logs if log.ip_address})

        return {
            "period_days": days,
            "facility_id": facility_id,
            "total_audit_events": len(logs),
            "unique_active_users": unique_users,
            "unique_ip_addresses": unique_ips,
            "security_metrics": {
                "successful_logins": len(login_logs),
                "failed_logins": len(failed_logins),
                "user_accounts_created": len(user_creation_logs),
                "login_success_rate": (
                    len(login_logs) / max(len(login_logs) + len(failed_logins), 1)
                )
                * 100,
            },
            "data_access_metrics": {
                "patient_record_access": len(patient_access_logs),
                "referral_access": len(referral_access_logs),
                "total_data_access": len(patient_access_logs)
                + len(referral_access_logs),
            },
            "data_modification_metrics": {
                "records_created": len(create_logs),
                "records_updated": len(update_logs),
                "records_deleted": len(delete_logs),
                "total_modifications": len(create_logs)
                + len(update_logs)
                + len(delete_logs),
            },
            "file_operations": {
                "files_uploaded": len(upload_logs),
                "files_downloaded": len(download_logs),
                "total_file_operations": len(upload_logs) + len(download_logs),
            },
        }

    def detect_anomalies(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Detect potential security anomalies in audit logs.

        Args:
            days: Number of days to analyze

        Returns:
            List of detected anomalies
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        anomalies = []

        # Get recent logs
        logs = self.db.query(AuditLog).filter(AuditLog.created_at >= start_date).all()

        # Anomaly 1: Unusual login patterns (multiple failed logins)
        failed_logins_by_user: Dict[int, int] = {}
        for log in logs:
            if log.action == "login_failed":
                user_id = log.user_id
                failed_logins_by_user[user_id] = (
                    failed_logins_by_user.get(user_id, 0) + 1
                )

        for user_id, failed_count in failed_logins_by_user.items():
            if failed_count >= 5:  # Threshold for suspicious activity
                user = self.db.query(User).filter(User.id == user_id).first()
                anomalies.append(
                    {
                        "type": "suspicious_login_activity",
                        "severity": "high",
                        "user_id": user_id,
                        "user_name": f"{user.first_name} {user.last_name}"
                        if user
                        else "Unknown",
                        "details": f"{failed_count} failed login attempts in {days} days",
                        "recommendation": "Review account security and consider password reset",
                    }
                )

        # Anomaly 2: Unusual data access patterns
        access_by_user = {}
        for log in logs:
            if log.action in [AuditAction.VIEW.value, AuditAction.DOWNLOAD.value]:
                user_id = log.user_id
                access_by_user[user_id] = access_by_user.get(user_id, 0) + 1

        # Flag users with unusually high access
        avg_access = sum(access_by_user.values()) / max(len(access_by_user), 1)
        threshold = avg_access * 3  # 3x average access

        for user_id, access_count in access_by_user.items():
            if access_count > threshold:
                user = self.db.query(User).filter(User.id == user_id).first()
                anomalies.append(
                    {
                        "type": "unusual_data_access",
                        "severity": "medium",
                        "user_id": user_id,
                        "user_name": f"{user.first_name} {user.last_name}"
                        if user
                        else "Unknown",
                        "details": f"{access_count} data access events (average: {avg_access:.1f})",
                        "recommendation": "Review data access patterns for compliance",
                    }
                )

        # Anomaly 3: Unusual IP addresses
        ip_by_user = {}
        for log in logs:
            if log.ip_address:
                user_id = log.user_id
                if user_id not in ip_by_user:
                    ip_by_user[user_id] = set()
                ip_by_user[user_id].add(log.ip_address)

        for user_id, ip_set in ip_by_user.items():
            if len(ip_set) > 5:  # User accessing from many different IPs
                user = self.db.query(User).filter(User.id == user_id).first()
                anomalies.append(
                    {
                        "type": "multiple_ip_addresses",
                        "severity": "medium",
                        "user_id": user_id,
                        "user_name": f"{user.first_name} {user.last_name}"
                        if user
                        else "Unknown",
                        "details": f"Access from {len(ip_set)} different IP addresses",
                        "recommendation": "Verify account security and access patterns",
                    }
                )

        return anomalies

    def export_audit_logs(
        self, format: str = "json", filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Export audit logs in specified format.

        Args:
            format: Export format (json, csv)
            filters: Optional filters to apply

        Returns:
            Exported data as string
        """
        # Apply filters
        logs = self.get_audit_logs(**(filters or {}))

        if format.lower() == "json":
            import json

            return json.dumps(
                [
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "action": log.action,
                        "entity_type": log.entity_type,
                        "entity_id": log.entity_id,
                        "details": log.details,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ],
                indent=2,
            )

        elif format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(
                [
                    "id",
                    "user_id",
                    "action",
                    "entity_type",
                    "entity_id",
                    "details",
                    "ip_address",
                    "created_at",
                ]
            )

            # Data
            for log in logs:
                writer.writerow(
                    [
                        log.id,
                        log.user_id,
                        log.action,
                        log.entity_type,
                        log.entity_id,
                        log.details,
                        log.ip_address,
                        log.created_at.isoformat(),
                    ]
                )

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def cleanup_old_logs(self, days_to_keep: int = 365) -> int:
        """
        Clean up old audit logs to manage storage.

        Args:
            days_to_keep: Number of days to keep logs

        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        deleted_count = (
            self.db.query(AuditLog).filter(AuditLog.created_at < cutoff_date).delete()
        )

        self.db.commit()
        return deleted_count


def get_audit_service(db: Session) -> AuditService:
    """Get audit service instance."""
    return AuditService(db)
