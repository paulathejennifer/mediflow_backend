from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.referral import Referral
from app.models.facility import Facility
from app.models.patient import Patient
from app.enums import UserRole, ReferralStatus, Priority
from sqlalchemy import and_, or_, func

router = APIRouter()


@router.get("/referrals")
def get_referral_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get referral analytics for the current user's scope.
    
    - Super Admin: System-wide analytics
    - Facility Admin/Clinician: Facility-specific analytics
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Build base query based on user role
    base_query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN:
        if not current_user.facility_id:
            return {
                "error": "User not assigned to a facility",
                "period_days": days,
                "total_referrals": 0,
                "sent_referrals": 0,
                "received_referrals": 0,
                "status_breakdown": {},
                "priority_breakdown": {},
                "avg_processing_time_hours": 0,
                "acceptance_rate": 0,
            }
        
        # Filter by user's facility (sender or receiver)
        base_query = base_query.filter(
            and_(
                or_(
                    Referral.from_facility_id == current_user.facility_id,
                    Referral.to_facility_id == current_user.facility_id,
                ),
                Referral.created_at >= start_date,
            )
        )
    else:
        # Super admin sees all referrals in the time period
        base_query = base_query.filter(Referral.created_at >= start_date)
    
    # Total referrals
    total_referrals = base_query.count()
    
    # Sent vs received (only meaningful for facility users)
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        sent_referrals = base_query.filter(
            Referral.from_facility_id == current_user.facility_id
        ).count()
        received_referrals = base_query.filter(
            Referral.to_facility_id == current_user.facility_id
        ).count()
    else:
        sent_referrals = total_referrals  # For super admin, all are "sent" in a sense
        received_referrals = 0
    
    # Status breakdown
    status_breakdown = {}
    for status in ReferralStatus:
        count = base_query.filter(Referral.status == status.value).count()
        status_breakdown[status.value] = count
    
    # Priority breakdown
    priority_breakdown = {}
    for priority in Priority:
        count = base_query.filter(Referral.priority == priority.value).count()
        priority_breakdown[priority.value] = count
    
    # Average processing time (from created to last updated for accepted referrals)
    processing_times = []
    accepted_referrals = base_query.filter(
        Referral.status == ReferralStatus.ACCEPTED.value
    ).all()
    
    for referral in accepted_referrals:
        if referral.updated_at and referral.created_at:
            processing_time = (
                referral.updated_at - referral.created_at
            ).total_seconds() / 3600  # hours
            processing_times.append(processing_time)
    
    avg_processing_time = (
        sum(processing_times) / len(processing_times) if processing_times else 0
    )
    
    # Acceptance rate
    submitted_count = status_breakdown.get(ReferralStatus.SUBMITTED.value, 0)
    accepted_count = status_breakdown.get(ReferralStatus.ACCEPTED.value, 0)
    completed_count = status_breakdown.get(ReferralStatus.COMPLETED.value, 0)
    
    acceptance_rate = (
        (accepted_count + completed_count) / max(submitted_count, 1)
    ) * 100 if submitted_count > 0 else 0
    
    return {
        "period_days": days,
        "total_referrals": total_referrals,
        "sent_referrals": sent_referrals,
        "received_referrals": received_referrals,
        "status_breakdown": status_breakdown,
        "priority_breakdown": priority_breakdown,
        "avg_processing_time_hours": round(avg_processing_time, 2),
        "acceptance_rate": round(acceptance_rate, 2),
    }


@router.get("/dashboard")
def get_dashboard_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get dashboard KPIs for the current user.
    
    Returns key metrics for dashboard display.
    """
    # Get last 30 days of data
    days = 30
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Build base query based on user role
    referral_query = db.query(Referral)
    patient_query = db.query(Patient)
    facility_query = db.query(Facility)
    
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin sees everything
        total_patients = patient_query.count()
        total_facilities = facility_query.count()
        total_referrals = referral_query.filter(
            Referral.created_at >= start_date
        ).count()
        
        # Active referrals (not completed or rejected)
        active_statuses = [
            ReferralStatus.DRAFT.value,
            ReferralStatus.SUBMITTED.value,
            ReferralStatus.ACCEPTED.value,
            ReferralStatus.IN_TRANSIT.value,
            ReferralStatus.RECEIVED.value,
        ]
        active_referrals = referral_query.filter(
            Referral.status.in_(active_statuses)
        ).count()
        
        # Pending referrals (submitted but not yet accepted/rejected)
        pending_referrals = referral_query.filter(
            Referral.status == ReferralStatus.SUBMITTED.value
        ).count()
        
        # Rejection rate
        total_with_outcome = referral_query.filter(
            Referral.status.in_([
                ReferralStatus.COMPLETED.value,
                ReferralStatus.REJECTED.value,
            ])
        ).count()
        rejected_count = referral_query.filter(
            Referral.status == ReferralStatus.REJECTED.value
        ).count()
        rejection_rate = (
            (rejected_count / max(total_with_outcome, 1)) * 100
        ) if total_with_outcome > 0 else 0
        
        # System utilization (referrals per facility)
        avg_referrals_per_facility = (
            total_referrals / max(total_facilities, 1)
        )
        
        return {
            "total_patients": total_patients,
            "total_facilities": total_facilities,
            "total_referrals_30d": total_referrals,
            "active_referrals": active_referrals,
            "pending_referrals": pending_referrals,
            "rejection_rate": round(rejection_rate, 2),
            "avg_referrals_per_facility": round(avg_referrals_per_facility, 1),
            "system_utilization_percent": min(
                round((total_referrals / max(total_facilities * 100, 1)) * 100, 1),
                100
            ),
        }
    
    elif current_user.facility_id:
        # Facility-based user
        facility_id = current_user.facility_id
        
        # Patients from this facility
        total_patients = patient_query.join(
            # Assuming there's a relationship through patient_identifiers
        ).filter(
            # Filter by facility - adjust based on actual schema
        ).count()
        
        # For simplicity, count all patients (facility isolation happens at service layer)
        total_patients = patient_query.count()
        
        # Referrals for this facility
        facility_referrals = referral_query.filter(
            and_(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id,
                ),
                Referral.created_at >= start_date,
            )
        )
        
        total_referrals = facility_referrals.count()
        
        # Sent from this facility
        sent_referrals = facility_referrals.filter(
            Referral.from_facility_id == facility_id
        ).count()
        
        # Received by this facility
        received_referrals = facility_referrals.filter(
            Referral.to_facility_id == facility_id
        ).count()
        
        # Active referrals
        active_statuses = [
            ReferralStatus.DRAFT.value,
            ReferralStatus.SUBMITTED.value,
            ReferralStatus.ACCEPTED.value,
            ReferralStatus.IN_TRANSIT.value,
            ReferralStatus.RECEIVED.value,
        ]
        active_referrals = facility_referrals.filter(
            Referral.status.in_(active_statuses)
        ).count()
        
        # Pending (submitted, awaiting response)
        pending_referrals = facility_referrals.filter(
            Referral.status == ReferralStatus.SUBMITTED.value
        ).count()
        
        # This facility's info
        facility = facility_query.filter(
            Facility.id == facility_id
        ).first()
        
        return {
            "facility_name": facility.name if facility else "Unknown",
            "total_patients": total_patients,
            "total_referrals_30d": total_referrals,
            "sent_referrals_30d": sent_referrals,
            "received_referrals_30d": received_referrals,
            "active_referrals": active_referrals,
            "pending_referrals": pending_referrals,
            "facility_utilization_percent": min(
                round((total_referrals / 100) * 100, 1),  # Assuming 100 referrals is 100% capacity
                100
            ),
        }
    
    else:
        # User without facility
        return {
            "error": "User not assigned to a facility",
            "total_patients": 0,
            "total_referrals_30d": 0,
            "active_referrals": 0,
            "pending_referrals": 0,
        }


@router.get("/referrals/by-status")
def get_referrals_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referrals grouped by status for pie chart visualization."""
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        query = query.filter(
            or_(
                Referral.from_facility_id == current_user.facility_id,
                Referral.to_facility_id == current_user.facility_id,
            )
        )
    
    status_counts = {}
    for status in ReferralStatus:
        count = query.filter(Referral.status == status.value).count()
        if count > 0:
            status_counts[status.value] = count
    
    return {
        "labels": list(status_counts.keys()),
        "data": list(status_counts.values()),
        "total": sum(status_counts.values()),
    }


@router.get("/referrals/by-priority")
def get_referrals_by_priority(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referrals grouped by priority for chart visualization."""
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        query = query.filter(
            or_(
                Referral.from_facility_id == current_user.facility_id,
                Referral.to_facility_id == current_user.facility_id,
            )
        )
    
    priority_counts = {}
    for priority in Priority:
        count = query.filter(Referral.priority == priority.value).count()
        if count > 0:
            priority_counts[priority.value] = count
    
    return {
        "labels": list(priority_counts.keys()),
        "data": list(priority_counts.values()),
        "total": sum(priority_counts.values()),
    }


@router.get("/referrals/trend")
def get_referral_trend(
    days: int = Query(30, ge=7, le=90, description="Number of days for trend analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referral trend over time for line chart visualization."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        query = query.filter(
            and_(
                or_(
                    Referral.from_facility_id == current_user.facility_id,
                    Referral.to_facility_id == current_user.facility_id,
                ),
                Referral.created_at >= start_date,
                Referral.created_at <= end_date,
            )
        )
    else:
        query = query.filter(
            Referral.created_at >= start_date,
            Referral.created_at <= end_date,
        )
    
    # Group by date
    referrals = query.order_by(Referral.created_at).all()
    
    # Create daily counts
    daily_counts = {}
    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_counts[date] = 0
    
    for referral in referrals:
        date = referral.created_at.strftime("%Y-%m-%d")
        if date in daily_counts:
            daily_counts[date] += 1
    
    return {
        "labels": list(daily_counts.keys()),
        "data": list(daily_counts.values()),
        "total": sum(daily_counts.values()),
        "average_per_day": round(sum(daily_counts.values()) / max(days, 1), 2),
    }


@router.get("/facilities/top-referring")
def get_top_referring_facilities(
    limit: int = Query(10, ge=1, le=50, description="Number of facilities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get top referring facilities for bar chart visualization."""
    # Only super admin can see all facilities
    if current_user.role != UserRole.SUPER_ADMIN:
        return {
            "error": "Only super admin can view this analytics",
            "labels": [],
            "data": [],
        }
    
    # Count referrals by from_facility
    facility_counts = (
        db.query(
            Referral.from_facility_id,
            func.count(Referral.id).label("referral_count"),
        )
        .group_by(Referral.from_facility_id)
        .order_by(func.count(Referral.id).desc())
        .limit(limit)
        .all()
    )
    
    labels = []
    data = []
    
    for facility_id, count in facility_counts:
        facility = db.query(Facility).filter(Facility.id == facility_id).first()
        if facility:
            labels.append(facility.name)
            data.append(count)
    
    return {
        "labels": labels,
        "data": data,
        "total_referrals": sum(data),
    }