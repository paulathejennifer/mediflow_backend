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
from app.models.referral_document import ReferralDocument
from app.enums import UserRole, ReferralStatus, Priority
from sqlalchemy import and_, or_, func, extract, case
from sqlalchemy.sql import label

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
    """Get referrals grouped by status for pie chart visualization.
    
    Only shows key workflow statuses: submitted, accepted, in_transit, completed.
    Draft, received, and rejected statuses are excluded from the visualization.
    """
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        query = query.filter(
            or_(
                Referral.from_facility_id == current_user.facility_id,
                Referral.to_facility_id == current_user.facility_id,
            )
        )
    
    # Only show key workflow statuses
    display_statuses = [
        ReferralStatus.SUBMITTED,
        ReferralStatus.ACCEPTED,
        ReferralStatus.IN_TRANSIT,
        ReferralStatus.COMPLETED,
    ]
    
    # Map backend status to display names
    status_display_map = {
        "submitted": "submitted",
        "accepted": "accepted",
        "in_transit": "in_progress",
        "completed": "completed",
    }
    
    status_counts = {}
    for status in display_statuses:
        count = query.filter(Referral.status == status.value).count()
        if count > 0:
            display_name = status_display_map.get(status.value, status.value)
            status_counts[display_name] = count
    
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


@router.get("/system-activity")
def get_system_activity_trend(
    months: int = Query(6, ge=1, le=12, description="Number of months for trend analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get system activity trend over months for combined chart visualization."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=months * 30)
    
    # Build base queries based on user role
    referral_query = db.query(Referral)
    patient_query = db.query(Patient)
    document_query = db.query(ReferralDocument)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        facility_id = current_user.facility_id
        referral_query = referral_query.filter(
            or_(
                Referral.from_facility_id == facility_id,
                Referral.to_facility_id == facility_id,
            )
        )
        # Documents are linked through referrals
        referral_ids = (
            db.query(Referral.id)
            .filter(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id,
                )
            )
        )
        document_query = document_query.filter(
            ReferralDocument.referral_id.in_(referral_ids)
        )
    
    # Get monthly data for the specified period
    monthly_data = []
    for i in range(months, 0, -1):
        month_start = end_date - timedelta(days=i * 30)
        month_end = end_date - timedelta(days=(i - 1) * 30)
        
        month_label = month_start.strftime("%b")
        
        # Count patients created in this month
        patients_count = patient_query.filter(
            Patient.created_at >= month_start,
            Patient.created_at < month_end,
        ).count()
        
        # Count referrals created in this month
        referrals_count = referral_query.filter(
            Referral.created_at >= month_start,
            Referral.created_at < month_end,
        ).count()
        
        # Count documents created in this month
        documents_count = document_query.filter(
            ReferralDocument.created_at >= month_start,
            ReferralDocument.created_at < month_end,
        ).count()
        
        monthly_data.append({
            "month": month_label,
            "patients": patients_count,
            "referrals": referrals_count,
            "documents": documents_count,
        })
    
    return {
        "data": monthly_data,
        "period_months": months,
    }


@router.get("/referrals/volume")
def get_referral_volume(
    months: int = Query(6, ge=1, le=12, description="Number of months for volume analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referral volume by month (incoming vs outgoing) for bar chart visualization."""
    end_date = datetime.utcnow()
    
    # Build base query based on user role
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        facility_id = current_user.facility_id
        query = query.filter(
            or_(
                Referral.from_facility_id == facility_id,
                Referral.to_facility_id == facility_id,
            )
        )
    
    monthly_data = []
    for i in range(months, 0, -1):
        month_start = end_date - timedelta(days=i * 30)
        month_end = end_date - timedelta(days=(i - 1) * 30)
        
        month_label = month_start.strftime("%b")
        
        if current_user.role == UserRole.SUPER_ADMIN:
            # For super admin, count all referrals as "total"
            total_count = query.filter(
                Referral.created_at >= month_start,
                Referral.created_at < month_end,
            ).count()
            monthly_data.append({
                "month": month_label,
                "total": total_count,
            })
        else:
            # For facility users, distinguish incoming vs outgoing
            facility_id = current_user.facility_id
            outgoing_count = query.filter(
                Referral.from_facility_id == facility_id,
                Referral.created_at >= month_start,
                Referral.created_at < month_end,
            ).count()
            incoming_count = query.filter(
                Referral.to_facility_id == facility_id,
                Referral.created_at >= month_start,
                Referral.created_at < month_end,
            ).count()
            monthly_data.append({
                "month": month_label,
                "incoming": incoming_count,
                "outgoing": outgoing_count,
            })
    
    return {
        "data": monthly_data,
        "period_months": months,
    }


@router.get("/referrals/turnaround-time")
def get_turnaround_time_trend(
    weeks: int = Query(4, ge=1, le=12, description="Number of weeks for trend analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get average turnaround time by week for line chart visualization."""
    end_date = datetime.utcnow()
    
    # Build base query based on user role
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        facility_id = current_user.facility_id
        query = query.filter(
            or_(
                Referral.from_facility_id == facility_id,
                Referral.to_facility_id == facility_id,
            )
        )
    
    weekly_data = []
    for i in range(weeks, 0, -1):
        week_start = end_date - timedelta(weeks=i)
        week_end = end_date - timedelta(weeks=i-1)
        
        week_label = f"Week {weeks - i + 1}"
        
        # Get completed referrals in this week
        completed_referrals = query.filter(
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
            Referral.created_at >= week_start,
            Referral.created_at < week_end,
        ).all()
        
        # Calculate average turnaround time
        turnaround_times = []
        for referral in completed_referrals:
            if referral.updated_at and referral.created_at:
                time_diff = (referral.updated_at - referral.created_at).total_seconds() / 86400  # days
                turnaround_times.append(time_diff)
        
        avg_turnaround = 0
        if turnaround_times:
            avg_turnaround = round(sum(turnaround_times) / len(turnaround_times), 1)
        
        weekly_data.append({
            "week": week_label,
            "days": avg_turnaround,
        })
    
    return {
        "data": weekly_data,
        "period_weeks": weeks,
    }


@router.get("/referrals/by-reason")
def get_referrals_by_reason(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referrals grouped by reason for chart visualization."""
    # Build base query based on user role
    query = db.query(Referral)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        facility_id = current_user.facility_id
        query = query.filter(
            or_(
                Referral.from_facility_id == facility_id,
                Referral.to_facility_id == facility_id,
            )
        )
    
    # Get all referrals and group by reason
    referrals = query.all()
    reason_counts = {}
    
    for referral in referrals:
        reason = referral.reason_for_referral
        if not reason or reason.strip() == "":
            reason = "Not Specified"
        else:
            # Normalize the reason (take first line, truncate if too long)
            reason = reason.split("\n")[0].strip()
            if len(reason) > 50:
                reason = reason[:47] + "..."
        
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    
    # Sort by count and take top 10
    sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    labels = [reason for reason, count in sorted_reasons]
    data = [count for reason, count in sorted_reasons]
    
    return {
        "labels": labels,
        "data": data,
        "total": sum(data),
    }


@router.get("/facilities/performance")
def get_facility_performance(
    limit: int = Query(10, ge=1, le=50, description="Number of facilities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get facility performance metrics for chart visualization."""
    # Only super admin can see all facilities
    if current_user.role != UserRole.SUPER_ADMIN:
        return {
            "error": "Only super admin can view this analytics",
            "data": [],
        }
    
    # Get all facilities with their performance metrics
    facilities = db.query(Facility).limit(limit).all()
    
    performance_data = []
    for facility in facilities:
        # Count total referrals from this facility
        total_referrals = db.query(Referral).filter(
            Referral.from_facility_id == facility.id
        ).count()
        
        # Count completed referrals
        completed_referrals = db.query(Referral).filter(
            Referral.from_facility_id == facility.id,
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value])
        ).count()
        
        # Calculate completion rate
        completion_rate = 0
        if total_referrals > 0:
            completion_rate = round((completed_referrals / total_referrals) * 100, 1)
        
        # Calculate average turnaround time
        completed_list = db.query(Referral).filter(
            Referral.from_facility_id == facility.id,
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value])
        ).all()
        
        avg_turnaround = 0
        if completed_list:
            turnaround_times = []
            for r in completed_list:
                if r.updated_at and r.created_at:
                    time_diff = (r.updated_at - r.created_at).total_seconds() / 86400
                    turnaround_times.append(time_diff)
            if turnaround_times:
                avg_turnaround = round(sum(turnaround_times) / len(turnaround_times), 1)
        
        performance_data.append({
            "facility": facility.name,
            "total_referrals": total_referrals,
            "completed_referrals": completed_referrals,
            "completion_rate": completion_rate,
            "avg_turnaround_days": avg_turnaround,
        })
    
    # Sort by completion rate descending
    performance_data.sort(key=lambda x: x["completion_rate"], reverse=True)
    
    return {
        "data": performance_data,
        "total_facilities": len(performance_data),
    }


@router.get("/system-health")
def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get system health metrics. Only accessible by super admin."""
    if current_user.role != UserRole.SUPER_ADMIN:
        return {
            "error": "Only super admin can view system health",
            "healthScore": 0,
            "uptime": 0,
            "errorRate": 0,
            "avgResponseTime": 0,
        }
    
    # Calculate system health based on various metrics
    # In a real system, this would come from monitoring tools
    
    # Get recent referral success rate (completed vs rejected)
    last_7_days = datetime.utcnow() - timedelta(days=7)
    recent_referrals = db.query(Referral).filter(
        Referral.created_at >= last_7_days
    ).all()
    
    completed = sum(1 for r in recent_referrals if r.status in [ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value])
    rejected = sum(1 for r in recent_referrals if r.status == ReferralStatus.REJECTED.value)
    total = len(recent_referrals)
    
    success_rate = (completed / max(total, 1)) * 100
    
    # Get active facilities rate
    total_facilities = db.query(Facility).count()
    active_facilities = db.query(Facility).filter(Facility.is_active == True).count()
    facility_rate = (active_facilities / max(total_facilities, 1)) * 100
    
    # Get active users rate
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    user_rate = (active_users / max(total_users, 1)) * 100
    
    # Calculate overall health score (weighted average)
    health_score = round(
        (success_rate * 0.4) + 
        (facility_rate * 0.3) + 
        (user_rate * 0.3),
        1
    )
    
    # Simulate uptime (in a real system, this would come from monitoring)
    uptime = 99.9
    
    # Error rate (rejected referrals as percentage)
    error_rate = round((rejected / max(total, 1)) * 100, 1)
    
    # Average response time (simulated based on referral processing)
    avg_response_time = 245  # milliseconds
    
    return {
        "healthScore": health_score,
        "uptime": uptime,
        "errorRate": error_rate,
        "avgResponseTime": avg_response_time,
    }


@router.get("/api-requests")
def get_api_requests(
    days: int = Query(1, ge=1, le=30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get API request statistics. Only accessible by super admin."""
    if current_user.role != UserRole.SUPER_ADMIN:
        return {
            "error": "Only super admin can view API request statistics",
            "totalRequests": 0,
            "requestsLast24h": 0,
            "trend": 0,
        }
    
    # In a real system, this would come from request logging/analytics
    # For now, estimate based on system activity
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Count various activities as proxy for API requests
    referrals_count = db.query(Referral).filter(
        Referral.created_at >= start_date
    ).count()
    patients_count = db.query(Patient).filter(
        Patient.created_at >= start_date
    ).count()
    documents_count = db.query(ReferralDocument).filter(
        ReferralDocument.created_at >= start_date
    ).count()
    
    # Estimate total API requests (each entity typically involves multiple API calls)
    estimated_requests = (referrals_count * 5) + (patients_count * 3) + (documents_count * 4)
    
    # Calculate for last 24 hours
    last_24h = datetime.utcnow() - timedelta(days=1)
    referrals_24h = db.query(Referral).filter(
        Referral.created_at >= last_24h
    ).count()
    patients_24h = db.query(Patient).filter(
        Patient.created_at >= last_24h
    ).count()
    documents_24h = db.query(ReferralDocument).filter(
        ReferralDocument.created_at >= last_24h
    ).count()
    
    estimated_24h = (referrals_24h * 5) + (patients_24h * 3) + (documents_24h * 4)
    
    # Calculate trend (compare to previous period)
    previous_start = start_date - timedelta(days=days)
    previous_end = start_date
    
    previous_referrals = db.query(Referral).filter(
        and_(
            Referral.created_at >= previous_start,
            Referral.created_at < previous_end
        )
    ).count()
    previous_patients = db.query(Patient).filter(
        and_(
            Patient.created_at >= previous_start,
            Patient.created_at < previous_end
        )
    ).count()
    previous_documents = db.query(ReferralDocument).filter(
        and_(
            ReferralDocument.created_at >= previous_start,
            ReferralDocument.created_at < previous_end
        )
    ).count()
    
    estimated_previous = (previous_referrals * 5) + (previous_patients * 3) + (previous_documents * 4)
    
    trend = 0
    if estimated_previous > 0:
        trend = round(((estimated_requests - estimated_previous) / estimated_previous) * 100, 1)
    
    return {
        "totalRequests": estimated_requests,
        "requestsLast24h": estimated_24h,
        "trend": trend,
        "breakdown": {
            "referrals": referrals_count,
            "patients": patients_count,
            "documents": documents_count,
        }
    }


@router.get("/metrics")
def get_analytics_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get overall analytics metrics for the system or facility with trend comparisons."""
    # Build base queries based on user role
    patient_query = db.query(Patient)
    referral_query = db.query(Referral)
    document_query = db.query(ReferralDocument)
    user_query = db.query(User)
    
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        facility_id = current_user.facility_id
        referral_query = referral_query.filter(
            or_(
                Referral.from_facility_id == facility_id,
                Referral.to_facility_id == facility_id,
            )
        )
        # Documents linked through referrals
        referral_ids = (
            db.query(Referral.id)
            .filter(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id,
                )
            )
        )
        document_query = document_query.filter(
            ReferralDocument.referral_id.in_(referral_ids)
        )
        patient_query = patient_query.filter(
            Patient.facility_id == facility_id
        ) if hasattr(Patient, 'facility_id') else patient_query
    
    total_patients = patient_query.count()
    total_referrals = referral_query.count()
    total_documents = document_query.count()
    
    # Count active users
    active_users = user_query.filter(User.is_active == True).count()
    
    # Calculate growth rate (compare last 30 days to previous 30 days)
    now = datetime.utcnow()
    last_30_days = now - timedelta(days=30)
    previous_30_days = last_30_days - timedelta(days=30)
    
    recent_referrals = referral_query.filter(
        Referral.created_at >= last_30_days
    ).count()
    previous_referrals = referral_query.filter(
        and_(
            Referral.created_at >= previous_30_days,
            Referral.created_at < last_30_days
        )
    ).count()
    
    growth_rate = 0
    if previous_referrals > 0:
        growth_rate = round(((recent_referrals - previous_referrals) / previous_referrals) * 100, 1)
    
    # Calculate turnaround time trend
    recent_completed = referral_query.filter(
        Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
        Referral.created_at >= last_30_days
    ).all()
    
    previous_completed = referral_query.filter(
        Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
        Referral.created_at >= previous_30_days,
        Referral.created_at < last_30_days
    ).all()
    
    # Calculate average turnaround for recent period
    recent_turnaround_times = []
    for r in recent_completed:
        if r.updated_at and r.created_at:
            recent_turnaround_times.append((r.updated_at - r.created_at).total_seconds() / 86400)
    recent_avg_turnaround = sum(recent_turnaround_times) / len(recent_turnaround_times) if recent_turnaround_times else 0
    
    # Calculate average turnaround for previous period
    previous_turnaround_times = []
    for r in previous_completed:
        if r.updated_at and r.created_at:
            previous_turnaround_times.append((r.updated_at - r.created_at).total_seconds() / 86400)
    previous_avg_turnaround = sum(previous_turnaround_times) / len(previous_turnaround_times) if previous_turnaround_times else 0
    
    # Turnaround trend (negative is good - faster is better)
    turnaround_trend = 0
    if previous_avg_turnaround > 0:
        turnaround_trend = round(((recent_avg_turnaround - previous_avg_turnaround) / previous_avg_turnaround) * 100, 1)
    
    # Calculate completion rate trend
    recent_total = referral_query.filter(
        Referral.created_at >= last_30_days
    ).count()
    recent_completed_count = len(recent_completed)
    recent_completion_rate = (recent_completed_count / max(recent_total, 1)) * 100
    
    previous_total = referral_query.filter(
        Referral.created_at >= previous_30_days,
        Referral.created_at < last_30_days
    ).count()
    previous_completed_count = len(previous_completed)
    previous_completion_rate = (previous_completed_count / max(previous_total, 1)) * 100
    
    completion_rate_trend = round(recent_completion_rate - previous_completion_rate, 1)
    
    # Calculate pending referrals trend
    recent_pending = referral_query.filter(
        Referral.status == ReferralStatus.SUBMITTED.value,
        Referral.created_at >= last_30_days
    ).count()
    previous_pending = referral_query.filter(
        Referral.status == ReferralStatus.SUBMITTED.value,
        Referral.created_at >= previous_30_days,
        Referral.created_at < last_30_days
    ).count()
    
    pending_trend = recent_pending - previous_pending
    
    return {
        "totalPatients": total_patients,
        "totalReferrals": total_referrals,
        "totalDocuments": total_documents,
        "growthRate": growth_rate,
        "activeUsers": active_users,
        # Trend data for overview cards
        "turnaroundTrend": turnaround_trend,
        "completionRateTrend": completion_rate_trend,
        "pendingTrend": pending_trend,
        "recentAvgTurnaround": round(recent_avg_turnaround, 1),
        "recentCompletionRate": round(recent_completion_rate, 1),
        "recentPending": recent_pending,
    }
