"""
Notification Service for MediFlow System

This service handles the core logic for creating, managing, and distributing notifications
based on system events and user roles.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, JSON, cast

from app.models.notifications import (
    Notification,
    NotificationDelivery,
    NotificationTemplate,
    SystemMetric,
    NotificationPreference,
    NotificationQueue,
)
from app.models.user import User
from app.models.facility import Facility
from app.models.referral import Referral
from app.models.patient import Patient
from app.models.audit_log import AuditLog
from app.websocket.manager import notification_broadcaster
from app.core.security import get_password_hash
from app.enums import ReferralStatus, UserRole, AuditAction, Priority
from app.services.notification_events import NotificationEventCreators

logger = logging.getLogger(__name__)


class NotificationService(NotificationEventCreators):
    """Core notification service"""

    def __init__(self, db: Session):
        self.db = db
        self.broadcaster = notification_broadcaster

    def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        actions: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
        backend_source: str = "system",
        trigger_condition: Optional[str] = None,
        facility_id: Optional[int] = None,
        user_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> Notification:
        """Create a new notification"""

        if not roles:
            roles = ["super_admin"]  # Default to super admin if no roles specified

        notification = Notification(
            user_id=user_id,
            facility_id=facility_id,
            notification_type=notification_type,
            title=title,
            message=message,
            details=details or {},
            actions=actions or [],
            roles=roles,
            backend_source=backend_source,
            trigger_condition=trigger_condition,
            expires_at=expires_at,
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        logger.info(f"Created notification {notification.id}: {title}")

        # Broadcast notification immediately using a background task.
        # We pass the ID to avoid session-closed errors in async tasks.
        import asyncio
        asyncio.create_task(
            self.broadcaster.broadcast_notification(notification.id)
        )

        return notification

    def get_user_notifications(
        self,
        user_id: int,
        user_role: str,
        notification_type: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
        facility_id: Optional[int] = None,
    ) -> List[Notification]:
        """Get notifications for a specific user"""

        # Join with delivery to get user-specific read status for broadcast messages
        query = self.db.query(Notification, NotificationDelivery.delivery_status).outerjoin(
            NotificationDelivery, 
            and_(
                NotificationDelivery.notification_id == Notification.id,
                NotificationDelivery.user_id == user_id
            )
        ).filter(
            or_(
                Notification.user_id == user_id,
                and_(
                    Notification.user_id.is_(None),
                    # PostgreSQL specific JSONB containment operator
                    Notification.roles.op('@>')([user_role]),
                    # If a facility_id is set on the notification, it MUST match the user's facility.
                    # If it's NULL, it's a global system-wide broadcast.
                    and_(
                        or_(
                            Notification.facility_id.is_(None),
                            Notification.facility_id == facility_id
                        )
                    )
                ),
            )
        )

        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)

        if unread_only:
            # For broadcast, check delivery status. For direct, check is_read.
            query = query.filter(
                or_(
                    and_(Notification.user_id == user_id, Notification.is_read == False),
                    and_(Notification.user_id.is_(None), or_(
                        NotificationDelivery.id.is_(None),
                        NotificationDelivery.delivery_status != "read"
                    ))
                )
            )

        # Filter out expired notifications
        query = query.filter(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.now(timezone.utc),
            )
        )

        results = query.order_by(Notification.created_at.desc()).limit(limit).all()
        
        # Map results to include user-specific read status
        notifications = []
        for notif, delivery_status in results:
            # A notification is "read" for this user if:
            # 1. It's a direct notification and is_read is True
            # 2. It's a broadcast and there's a delivery record marked 'read'
            user_is_read = notif.is_read if notif.user_id == user_id else (delivery_status == "read")
            notif.user_specific_read = user_is_read
            notifications.append(notif)
            
        return notifications

    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read"""
        notification = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            return False

        # If it's a direct notification, update the main record
        if notification.user_id == user_id:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
        
        # Update or create delivery record to track per-user read state (for broadcasts)
        delivery = self.db.query(NotificationDelivery).filter(
            NotificationDelivery.notification_id == notification_id,
            NotificationDelivery.user_id == user_id
        ).first()

        if not delivery:
            delivery = NotificationDelivery(
                notification_id=notification_id,
                user_id=user_id,
                delivery_method="websocket",
                delivery_status="read",
                delivered_at=datetime.now(timezone.utc),
                read_at=datetime.now(timezone.utc)
            )
            self.db.add(delivery)
        else:
            delivery.delivery_status = "read"
            delivery.read_at = datetime.now(timezone.utc)

        self.db.commit()
        return True

    def mark_all_as_read(self, user_id: int, user_role: str) -> int:
        """Mark all relevant notifications for a user as read (powers /read-all)"""
        notifications = self.get_user_notifications(user_id, user_role, unread_only=True)
        count = 0
        for notif in notifications:
            if self.mark_notification_read(notif.id, user_id):
                count += 1
        return count

    def handle_notification_action(self, notification_id: int, user_id: int, action_id: str) -> Dict[str, Any]:
        """Process an action from a notification button (powers /actions/{id})"""
        notification = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise ValueError("Notification not found")

        # Log the action in the delivery table
        delivery = self.db.query(NotificationDelivery).filter(
            NotificationDelivery.notification_id == notification_id,
            NotificationDelivery.user_id == user_id
        ).first()

        if delivery:
            delivery.action_taken = action_id
            delivery.read_at = datetime.now(timezone.utc)
            self.db.commit()
        
        return {"status": "success", "action": action_id, "notification_id": notification_id}

    def get_user_role(self, user_id: int) -> str:
        """Get user's role"""
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.role if user else "unknown"

    # Event-based notification creators

    def create_emergency_referral_notification(
        self, referral: Referral
    ) -> Notification:
        """Create emergency referral notification"""

        roles = ["facility_admin", "clinician"]  # Shared by both

        notification = self.create_notification(
            notification_type="critical",
            title="🚨 EMERGENCY REFERRAL",
            message=f"Cardiac patient requires immediate transfer",
            details={
                "patient_id": f"P-{referral.patient_id}",
                "urgency": "life-threatening",
                "referral_id": f"R-{referral.id}",
                "time_sensitive": "30 minutes",
                "referring_facility": referral.from_facility.name
                if referral.from_facility
                else "Unknown",
            },
            actions=["📋 Accept Referral", "📞 Contact Referring MD"],
            roles=roles,
            backend_source="referrals",
            trigger_condition=f"referral.priority === 'emergency' && referral.id === {referral.id}",
            facility_id=referral.to_facility_id,
        )

        return notification

    def create_hipaa_violation_notification(self, audit_log: AuditLog) -> Notification:
        """Create HIPAA violation notification"""

        roles = ["facility_admin", "clinician"]  # Shared by both

        notification = self.create_notification(
            notification_type="critical",
            title="🔒 HIPAA COMPLIANCE VIOLATION",
            message="Unauthorized patient record access detected",
            details={
                "user_id": audit_log.user_id,
                "accessed_records": audit_log.details.get("accessed_count", 0),
                "authorization_level": "insufficient",
                "audit_log_id": f"A-{audit_log.id}",
                "facility": audit_log.user.facility.name
                if audit_log.user and audit_log.user.facility
                else "Unknown",
            },
            actions=["🚨 Suspend User", "📋 File Compliance Report"],
            roles=roles,
            backend_source="audit_logs",
            trigger_condition=f"audit.action === 'access_denied' && audit.details.unauthorized_access === true",
        )

        return notification

    def create_ai_service_down_notification(
        self, service_name: str, error_details: Dict[str, Any]
    ) -> Notification:
        """Create AI service down notification"""

        notification = self.create_notification(
            notification_type="critical",
            title="🚨 AI SERVICES OFFLINE",
            message=f"{service_name} service unreachable",
            details={
                "service": service_name,
                "endpoint": "/api/v1/ai/health",
                "error_count": error_details.get("error_count", 0),
                "last_success": error_details.get("last_success"),
            },
            actions=["🔧 Restart Services", "📊 Check System Logs"],
            roles=["super_admin"],
            backend_source="ai_services",
            trigger_condition=f"ai_service.health === 'down' && service === '{service_name}'",
        )

        return notification

    def create_referral_delay_notification(
        self, facility_id: int, delay_details: Dict[str, Any]
    ) -> Notification:
        """Create referral processing delay notification"""

        roles = ["facility_admin", "clinician"]  # Shared by both

        notification = self.create_notification(
            notification_type="warning",
            title="⚠️ REFERRAL PROCESSING DELAYS",
            message="Average processing time exceeded SLA",
            details={
                "sla_target": delay_details.get("sla_target", "2 hours"),
                "current_avg": delay_details.get("current_avg", "3.8 hours"),
                "backlog_count": delay_details.get("backlog_count", 45),
                "affected_departments": delay_details.get(
                    "affected_departments", ["Cardiology", "Neurology"]
                ),
            },
            actions=["📋 Review Backlog", "👥 Reassign Staff"],
            roles=roles,
            backend_source="referrals",
            trigger_condition="referral.processing_time > sla_target * 1.5",
        )

        return notification

    def create_ai_performance_notification(
        self, performance_details: Dict[str, Any]
    ) -> Notification:
        """Create AI performance degradation notification"""

        roles = ["facility_admin", "clinician"]  # Shared by both

        notification = self.create_notification(
            notification_type="warning",
            title="⚠️ AI PERFORMANCE DEGRADING",
            message="AI accuracy below threshold",
            details={
                "accuracy": performance_details.get("accuracy", "85%"),
                "required_minimum": "90%",
                "affected_services": performance_details.get(
                    "affected_services", ["whisper", "ocr"]
                ),
                "impact": performance_details.get("impact", "12 clinicians"),
            },
            actions=["🔧 Restart AI Services", "📊 View Analytics"],
            roles=roles,
            backend_source="ai_services",
            trigger_condition="ai.accuracy < required_minimum",
        )

        return notification

    def create_storage_warning_notification(
        self, facility_id: int, storage_details: Dict[str, Any]
    ) -> Notification:
        """Create storage capacity warning notification"""

        notification = self.create_notification(
            notification_type="warning",
            title="⚠️ FACILITY STORAGE WARNING",
            message="Document storage at 85% capacity",
            details={
                "used_storage": storage_details.get("used_storage", "4.2TB"),
                "total_storage": storage_details.get("total_storage", "5TB"),
                "days_until_full": storage_details.get("days_until_full", 7),
                "growth_rate": storage_details.get("growth_rate", "120GB/day"),
            },
            actions=["💾 Cleanup Storage", "📈 Request Upgrade"],
            roles=["facility_admin"],  # Facility admin only
            backend_source="file_system",
            trigger_condition="facility_storage.usage >= 85%",
        )

        return notification

    def create_storage_critical_notification(
        self, used_storage_gb: float, total_storage_gb: float
    ) -> Notification:
        """SA006: Create critical storage notification"""
        return self.create_notification(
            notification_type="critical",
            title="🚨 SYSTEM STORAGE CRITICAL",
            message=f"Server storage is nearly full ({used_storage_gb:.1f}GB / {total_storage_gb:.1f}GB)",
            details={
                "used_gb": used_storage_gb,
                "total_gb": total_storage_gb,
                "percent_used": (used_storage_gb / total_storage_gb) * 100
            },
            roles=["super_admin"],
            backend_source="system"
        )

    def create_referral_status_notification(self, referral: Referral) -> Notification:
        """Create referral status update notification"""

        roles = ["facility_admin", "clinician"]  # Shared by both

        notification = self.create_notification(
            notification_type="info",
            title="📋 REFERRAL STATUS UPDATE",
            message=f"Your {referral.priority} referral was {referral.status}",
            details={
                "patient_name": f"{referral.patient.first_name} {referral.patient.last_name}",
                "referral_id": f"R-{referral.id}",
                "accepting_facility": referral.to_facility.name
                if referral.to_facility
                else "Unknown",
                "accepting_physician": referral.accepted_by_user.first_name
                if referral.accepted_by_user
                else "Unknown",
                "estimated_arrival": referral.created_at.isoformat()
                if referral.created_at
                else None,
            },
            actions=["📋 View Details", "📞 Prepare Patient"],
            roles=roles,
            backend_source="referrals",
            trigger_condition=f"referral.status === '{referral.status}'",
            facility_id=referral.from_facility_id,
        )

        return notification

    def create_voice_note_transcribed_notification(
        self, voice_note_details: Dict[str, Any]
    ) -> Notification:
        """Create voice note transcription complete notification"""

        roles = ["facility_admin", "clinician"]  # Shared by both

        notification = self.create_notification(
            notification_type="info",
            title="🤖 VOICE NOTE TRANSCRIBED",
            message="Patient assessment transcription ready",
            details={
                "recording_duration": voice_note_details.get("duration", "12 minutes"),
                "accuracy": voice_note_details.get("accuracy", "96.8%"),
                "word_count": voice_note_details.get("word_count", 1247),
                "processing_time": voice_note_details.get(
                    "processing_time", "1.1 minutes"
                ),
            },
            actions=["📝 Review Transcript", "✅ Approve Note"],
            roles=roles,
            backend_source="voice_notes",
            trigger_condition="voice_note.status === 'transcribed'",
        )

        return notification

    def create_team_performance_notification(
        self, facility_id: int, performance_data: Dict[str, Any]
    ) -> Notification:
        """Create team performance notification"""

        notification = self.create_notification(
            notification_type="info",
            title="👥 WEEKLY TEAM PERFORMANCE",
            message="Clinician performance summary ready",
            details={
                "top_performer": performance_data.get(
                    "top_performer", "Dr. Mike Wilson"
                ),
                "avg_referral_time": performance_data.get(
                    "avg_referral_time", "1.2 hours"
                ),
                "patient_satisfaction": performance_data.get(
                    "patient_satisfaction", "4.7/5.0"
                ),
                "completion_rate": performance_data.get("completion_rate", "96%"),
            },
            actions=["🎉 Recognize Team", "📊 View Details"],
            roles=["facility_admin"],  # Facility admin only
            backend_source="analytics",
            trigger_condition="weekly_report_generated === true",
        )

        return notification

    # System monitoring methods

    def monitor_system_metrics(self):
        """Monitor system metrics and create notifications as needed"""

        # Monitor AI service health
        self.monitor_ai_services()

        # Monitor database performance
        self.monitor_database_performance()

        # Monitor storage usage
        self.monitor_storage_usage()

        # Monitor referral processing times
        self.monitor_referral_performance()

    def monitor_ai_services(self):
        """Monitor AI service health"""

        # This would check actual AI service health
        # For now, we'll create a placeholder implementation

        services = ["groq", "whisper", "tesseract"]

        for service in services:
            # Check if service is down (placeholder logic)
            is_down = self.check_service_health(service)

            if is_down:
                # Check if we already have a recent notification for this service
                recent_notification = (
                    self.db.query(Notification)
                    .filter(
                        Notification.backend_source == "ai_services",
                        Notification.details.contains({"service": service}),
                        Notification.created_at
                        > datetime.now(timezone.utc) - timedelta(hours=1),
                    )
                    .first()
                )

                if not recent_notification:
                    self.create_ai_service_down_notification(
                        service,
                        {
                            "error_count": 127,
                            "last_success": datetime.now(timezone.utc)
                            - timedelta(minutes=30),
                        },
                    )

    def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy (placeholder implementation)"""
        # This would actually check the service health
        # For now, return False to demonstrate the notification system
        return False

    def monitor_database_performance(self):
        """Monitor database performance metrics"""

        # Check connection pool usage
        # Check query performance
        # Check error rates

        # Placeholder implementation
        error_rate = 0.15  # 15% error rate

        if error_rate > 0.10:  # 10% threshold
            # Check for recent notification
            recent_notification = (
                self.db.query(Notification)
                .filter(
                    Notification.backend_source == "database",
                    Notification.notification_type == "critical",
                    Notification.created_at
                    > datetime.now(timezone.utc) - timedelta(hours=1),
                )
                .first()
            )

            if not recent_notification:
                self.create_notification(
                    notification_type="critical",
                    title="🚨 DATABASE PERFORMANCE ISSUES",
                    message="Database error rate exceeded threshold",
                    details={
                        "error_rate": f"{error_rate * 100:.1f}%",
                        "threshold": "10%",
                        "affected_queries": 45,
                    },
                    actions=["🔄 Restart Database", "📊 Monitor Connections"],
                    roles=["super_admin"],
                    backend_source="database",
                )

    def monitor_storage_usage(self):
        """Monitor storage usage across facilities"""

        facilities = self.db.query(Facility).filter(Facility.is_active == "true").all()

        for facility in facilities:
            # Check storage usage (placeholder implementation)
            storage_usage = 0.85  # 85% usage

            if storage_usage >= 0.85:  # 85% threshold
                # Check for recent notification
                recent_notification = (
                    self.db.query(Notification)
                    .filter(
                        Notification.backend_source == "file_system",
                        Notification.notification_type == "warning",
                        Notification.created_at
                        > datetime.now(timezone.utc) - timedelta(hours=24),
                    )
                    .first()
                )

                if not recent_notification:
                    self.create_storage_warning_notification(
                        facility.id,
                        {
                            "used_storage": "4.2TB",
                            "total_storage": "5TB",
                            "days_until_full": 7,
                            "growth_rate": "120GB/day",
                        },
                    )

    def monitor_referral_performance(self):
        """Monitor referral processing performance"""

        # Check for overdue referrals
        overdue_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        overdue_referrals = (
            self.db.query(Referral)
            .filter(
                Referral.status == ReferralStatus.PENDING,
                Referral.created_at < overdue_threshold,
            )
            .count()
        )

        if overdue_referrals > 40:  # Threshold for warning
            # Check for recent notification
            recent_notification = (
                self.db.query(Notification)
                .filter(
                    Notification.backend_source == "referrals",
                    Notification.notification_type == "warning",
                    Notification.created_at
                    > datetime.now(timezone.utc) - timedelta(hours=6),
                )
                .first()
            )

            if not recent_notification:
                self.create_referral_delay_notification(
                    None,
                    {
                        "sla_target": "2 hours",
                        "current_avg": "3.8 hours",
                        "backlog_count": overdue_referrals,
                        "affected_departments": ["Cardiology", "Neurology"],
                    },
                )

    def get_notification_stats(self, user_id: int, user_role: str) -> Dict[str, Any]:
        """Get notification statistics for a user"""

        notifications = self.get_user_notifications(user_id, user_role)

        stats = {
            "total": len(notifications),
            "unread": len([n for n in notifications if not n.is_read]),
            "critical": len(
                [n for n in notifications if n.notification_type == "critical"]
            ),
            "warning": len(
                [n for n in notifications if n.notification_type == "warning"]
            ),
            "info": len([n for n in notifications if n.notification_type == "info"]),
            "expired": len(
                [
                    n
                    for n in notifications
                    if n.expires_at and n.expires_at < datetime.now(timezone.utc)
                ]
            ),
        }

        return stats


def get_notification_service(db: Session) -> NotificationService:
    """Get notification service instance"""
    return NotificationService(db)
