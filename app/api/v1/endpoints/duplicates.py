from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.referral import Referral
from app.models.facility import Facility
# Import your newly added table logic here safely
try:
    from app.models.duplicate_patient import DuplicatePatientPair
except ImportError:
    DuplicatePatientPair = None

class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_kpi_dashboard_metrics(self) -> dict:
        """Aggregates system-wide key operational metrics, specialty groups, and trends."""
        
        # 1. Base counts
        total_referrals = self.db.query(Referral).count()
        pending_count = self.db.query(Referral).filter(Referral.status == "submitted").count()
        rejected_count = self.db.query(Referral).filter(Referral.status == "rejected").count()
        
        # 2. Track duplicate patients stopped or caught by the ML engine
        duplicates_prevented = 0
        if DuplicatePatientPair:
            duplicates_prevented = self.db.query(DuplicatePatientPair).filter(
                DuplicatePatientPair.status.in_(["flagged", "merged"])
            ).count()

        # 3. Status Distributions for pie charts
        status_query = self.db.query(Referral.status, func.count(Referral.id)).group_by(Referral.status).all()
        status_distribution = {status: count for status, count in status_query}

        # 4. Referrals breakdown by Priority Level
        priority_query = self.db.query(Referral.priority, func.count(Referral.id)).group_by(Referral.priority).all()
        priority_distribution = {priority: count for priority, count in priority_query}

        # 5. Top 5 Target receiving facilities for routing charts
        facility_query = (
            self.db.query(Facility.name, func.count(Referral.id).label("total"))
            .join(Referral, Referral.to_facility_id == Facility.id)
            .group_by(Facility.name)
            .order_by(text("total DESC") if hasattr(self.db, "dialect") else func.count(Referral.id).desc())
            .limit(5)
            .all()
        )
        top_facilities = [{"facility_name": name, "count": count} for name, count in facility_query]

        return {
            "summary_cards": {
                "total_referrals": total_referrals,
                "pending_referrals": pending_count,
                "rejected_referrals": rejected_count,
                "duplicates_prevented": duplicates_prevented
            },
            "charts": {
                "status_distribution": status_distribution,
                "priority_distribution": priority_distribution,
                "top_receiving_facilities": top_facilities
            }
        }