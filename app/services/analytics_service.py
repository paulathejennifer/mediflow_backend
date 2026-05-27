from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from app.models.referral import Referral
from app.models.patient import Patient
from app.models.referral_document import ReferralDocument
from app.models.audit_log import AuditLog

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_real_api_request_count(self, days: int = 1):
        """
        Returns structured count of audit log entries as a proxy for activity.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        prev_start_date = start_date - timedelta(days=days)
        
        # Current Period Count
        current_count = self.db.query(func.count(AuditLog.id)).filter(
            AuditLog.created_at >= start_date
        ).scalar() or 0

        # Previous Period Count (for trend)
        prev_count = self.db.query(func.count(AuditLog.id)).filter(
            and_(AuditLog.created_at >= prev_start_date, AuditLog.created_at < start_date)
        ).scalar() or 0
        
        # Get specific counts for the breakdown
        ref_count = self.db.query(func.count(AuditLog.id)).filter(
            and_(AuditLog.created_at >= start_date, AuditLog.entity_type == "referral")
        ).scalar() or 0
        pat_count = self.db.query(func.count(AuditLog.id)).filter(
            and_(AuditLog.created_at >= start_date, AuditLog.entity_type == "patient")
        ).scalar() or 0
        doc_count = self.db.query(func.count(AuditLog.id)).filter(
            and_(AuditLog.created_at >= start_date, AuditLog.entity_type == "document")
        ).scalar() or 0
        
        return {
            "totalRequests": current_count,
            "requestsLast24h": current_count,
            "trend": self.calculate_percentage_trend(current_count, prev_count),
            "breakdown": {
                "referrals": ref_count,
                "patients": pat_count,
                "documents": doc_count
            }
        }

    def calculate_percentage_trend(self, current: int, previous: int) -> float:
        if previous <= 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    def get_system_health_metrics(self):
        # This will contain logic currently in the endpoint to calculate health scores
        pass

    def get_dashboard_metrics(self, is_super_admin: bool, facility_id: int = None):
        # This will contain the complex KPI logic currently in analytics.py
        pass

def get_analytics_service(db: Session):
    return AnalyticsService(db)