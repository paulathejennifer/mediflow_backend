from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.referral import Referral
from app.models.facility import Facility
from app.models.patient_identifier import PatientIdentifier # Import PatientIdentifier
from app.models.patient import Patient
from app.models.referral_document import ReferralDocument
from app.enums import UserRole, ReferralStatus, Priority
from sqlalchemy import and_, or_, func, extract, case
from sqlalchemy.sql import label
from app.services.analytics_service import get_analytics_service

logger = logging.getLogger(__name__)

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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )
        
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
    
    # Status breakdown
    status_breakdown = {}
    for ref_status in ReferralStatus:
        count = base_query.filter(Referral.status == ref_status.value).count()
        status_breakdown[ref_status.value] = count
    
    # Priority breakdown
    priority_breakdown = {}
    

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
    - Super Admin: System-wide statistics
    - Facility Admin/Clinician: Facility-specific statistics
    """
    def calculate_trend(current: int, previous: int) -> float:
        if previous <= 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    try:
        days = 30
        start_date = datetime.utcnow() - timedelta(days=days)
        prev_start_date = start_date - timedelta(days=days)
        
        if current_user.role == UserRole.SUPER_ADMIN:
            # Super admin sees everything
            total_patients = db.query(Patient).count()
            
            # Calculate Patient Trend (Last 30 vs Previous 30)
            new_patients_current = db.query(Patient).filter(Patient.created_at >= start_date).count()
            new_patients_prev = db.query(Patient).filter(
                and_(Patient.created_at >= prev_start_date, Patient.created_at < start_date)
            ).count()
            patient_trend = calculate_trend(new_patients_current, new_patients_prev)
            
            # New Patients This Month (for Patients Page)
            new_patients_this_month = new_patients_current # Same as new_patients_current for 30-day window

            # Calculate User Trend
            total_users = db.query(User).count()
            new_users_current = db.query(User).filter(User.created_at >= start_date).count()
            new_users_prev = db.query(User).filter(
                and_(User.created_at >= prev_start_date, User.created_at < start_date)
            ).count()
            user_trend = calculate_trend(new_users_current, new_users_prev)

            # Calculate Role-specific Trends (for Staff Page)
            clinician_count = db.query(User).filter(User.role == UserRole.CLINICIAN.value).count()
            new_clinicians_current = db.query(User).filter(and_(User.role == UserRole.CLINICIAN.value, User.created_at >= start_date)).count()
            new_clinicians_prev = db.query(User).filter(and_(User.role == UserRole.CLINICIAN.value, User.created_at >= prev_start_date, User.created_at < start_date)).count()
            clinician_trend = calculate_trend(new_clinicians_current, new_clinicians_prev)

            admin_count = db.query(User).filter(User.role == UserRole.FACILITY_ADMIN.value).count()
            new_admins_current = db.query(User).filter(and_(User.role == UserRole.FACILITY_ADMIN.value, User.created_at >= start_date)).count()
            new_admins_prev = db.query(User).filter(and_(User.role == UserRole.FACILITY_ADMIN.value, User.created_at >= prev_start_date, User.created_at < start_date)).count()
            admin_trend = calculate_trend(new_admins_current, new_admins_prev)

            # Active Users Trend
            active_users_count = db.query(User).filter(User.is_active == True).count()
            new_active_current = db.query(User).filter(and_(User.is_active == True, User.created_at >= start_date)).count()
            new_active_prev = db.query(User).filter(and_(User.is_active == True, User.created_at >= prev_start_date, User.created_at < start_date)).count()
            active_trend = calculate_trend(new_active_current, new_active_prev)

            # Calculate Document Trend
            total_documents = db.query(ReferralDocument).count()
            new_docs_current = db.query(ReferralDocument).filter(ReferralDocument.created_at >= start_date).count()
            new_docs_prev = db.query(ReferralDocument).filter(
                and_(ReferralDocument.created_at >= prev_start_date, ReferralDocument.created_at < start_date)
            ).count()
            doc_trend = calculate_trend(new_docs_current, new_docs_prev)

            total_facilities = db.query(Facility).count()
            total_referrals = db.query(Referral).filter(
                Referral.created_at >= start_date
            ).count()
            
            # Calculate Referral Trend
            total_referrals_prev = db.query(Referral).filter(
                and_(Referral.created_at >= prev_start_date, Referral.created_at < start_date)
            ).count()
            referral_trend = calculate_trend(total_referrals, total_referrals_prev)

            # Active referrals (not completed or rejected)
            active_statuses = [
                ReferralStatus.DRAFT.value,
                ReferralStatus.SUBMITTED.value,
                ReferralStatus.ACCEPTED.value,
                ReferralStatus.IN_TRANSIT.value,
                ReferralStatus.RECEIVED.value,
            ]
            active_referrals = db.query(Referral).filter(
                Referral.status.in_(active_statuses)
            ).count()
            
            # Pending referrals (submitted but not yet accepted/rejected)
            pending_referrals = db.query(Referral).filter(
                Referral.status == ReferralStatus.SUBMITTED.value
            ).count()
            
            # Rejection rate
            total_with_outcome = db.query(Referral).filter(
                Referral.status.in_([
                    ReferralStatus.COMPLETED.value,
                    ReferralStatus.REJECTED.value,
                ])
            ).count()
            rejected_count = db.query(Referral).filter(
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
                "total_patients_trend": patient_trend,
                "total_users": total_users,
                "new_patients_this_month": new_patients_this_month,
                "new_patients_this_month_trend": patient_trend, # Trend for new patients
                "total_users_trend": user_trend,
                "active_users": active_users_count,
                "active_users_trend": active_trend,
                "clinicians_count": clinician_count,
                "clinicians_trend": clinician_trend,
                "facility_admins_count": admin_count,
                "facility_admins_trend": admin_trend,
                "total_facilities": total_facilities,
                "total_referrals_30d": total_referrals,
                "total_referrals_trend": referral_trend,
                "total_documents": total_documents,
                "total_documents_trend": doc_trend,
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
            # Facility-based user (Facility Admin or Clinician)
            facility_id = current_user.facility_id
            
            # Patients from this facility ONLY
            total_patients = db.query(Patient).join(PatientIdentifier).filter(
                PatientIdentifier.facility_id == facility_id
            ).count()
            
            # Facility Patient Trend
            new_patients_current = db.query(Patient).join(PatientIdentifier).filter(
                and_(PatientIdentifier.facility_id == facility_id, Patient.created_at >= start_date)
            ).count()
            new_patients_prev = db.query(Patient).join(PatientIdentifier).filter(
                and_(
                    PatientIdentifier.facility_id == facility_id, 
                    Patient.created_at >= prev_start_date, 
                    Patient.created_at < start_date
                )
            ).count()
            patient_trend = calculate_trend(new_patients_current, new_patients_prev)

            # New Patients This Month (for Patients Page)
            new_patients_this_month = new_patients_current

            # Facility User Trend
            total_users = db.query(User).filter(User.facility_id == facility_id).count()
            new_users_current = db.query(User).filter(
                and_(User.facility_id == facility_id, User.created_at >= start_date)
            ).count()
            new_users_prev = db.query(User).filter(
                and_(
                    User.facility_id == facility_id,
                    User.created_at >= prev_start_date,
                    User.created_at < start_date
                )
            ).count()
            user_trend = calculate_trend(new_users_current, new_users_prev)

            # Facility Role-specific Trends
            clinician_count = db.query(User).filter(and_(User.facility_id == facility_id, User.role == UserRole.CLINICIAN.value)).count()
            new_clinicians_current = db.query(User).filter(and_(User.facility_id == facility_id, User.role == UserRole.CLINICIAN.value, User.created_at >= start_date)).count()
            new_clinicians_prev = db.query(User).filter(and_(User.facility_id == facility_id, User.role == UserRole.CLINICIAN.value, User.created_at >= prev_start_date, User.created_at < start_date)).count()
            clinician_trend = calculate_trend(new_clinicians_current, new_clinicians_prev)

            admin_count = db.query(User).filter(and_(User.facility_id == facility_id, User.role == UserRole.FACILITY_ADMIN.value)).count()
            new_admins_current = db.query(User).filter(and_(User.facility_id == facility_id, User.role == UserRole.FACILITY_ADMIN.value, User.created_at >= start_date)).count()
            new_admins_prev = db.query(User).filter(and_(User.facility_id == facility_id, User.role == UserRole.FACILITY_ADMIN.value, User.created_at >= prev_start_date, User.created_at < start_date)).count()
            admin_trend = calculate_trend(new_admins_current, new_admins_prev)

            # Active Users Trend for Facility
            active_users_count = db.query(User).filter(and_(User.facility_id == facility_id, User.is_active == True)).count()
            new_active_current = db.query(User).filter(and_(User.facility_id == facility_id, User.is_active == True, User.created_at >= start_date)).count()
            new_active_prev = db.query(User).filter(and_(User.facility_id == facility_id, User.is_active == True, User.created_at >= prev_start_date, User.created_at < start_date)).count()
            active_trend = calculate_trend(new_active_current, new_active_prev)

            # Referrals for this facility
            facility_referrals = db.query(Referral).filter(
                and_(
                    or_(
                        Referral.from_facility_id == facility_id,
                        Referral.to_facility_id == facility_id,
                    ),
                    Referral.created_at >= start_date,
                )
            )
            
            total_referrals = facility_referrals.count()
            
            # Facility Referral Trend
            total_referrals_prev = db.query(Referral).filter(
                and_(
                    or_(Referral.from_facility_id == facility_id, Referral.to_facility_id == facility_id),
                    Referral.created_at >= prev_start_date,
                    Referral.created_at < start_date
                )
            ).count()
            referral_trend = calculate_trend(total_referrals, total_referrals_prev)
            
            # Document stats for facility
            referral_ids = db.query(Referral.id).filter(
                or_(Referral.from_facility_id == facility_id, Referral.to_facility_id == facility_id)
            ).subquery()
            
            total_documents = db.query(ReferralDocument).filter(
                ReferralDocument.referral_id.in_(referral_ids)
            ).count()
            new_docs_current = db.query(ReferralDocument).filter(
                and_(ReferralDocument.referral_id.in_(referral_ids), ReferralDocument.created_at >= start_date)
            ).count()
            new_docs_prev = db.query(ReferralDocument).filter(
                and_(
                    ReferralDocument.referral_id.in_(referral_ids),
                    ReferralDocument.created_at >= prev_start_date,
                    ReferralDocument.created_at < start_date
                )
            ).count()
            doc_trend = calculate_trend(new_docs_current, new_docs_prev)

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
            facility = db.query(Facility).filter(
                Facility.id == facility_id
            ).first()
            
            return {
                "facility_name": facility.name if facility else "Unknown",
                "total_patients": total_patients,
                "total_patients_trend": patient_trend,
                "new_patients_this_month": new_patients_this_month,
                "new_patients_this_month_trend": patient_trend,
                "total_users": total_users,
                "total_users_trend": user_trend,
                "active_users": active_users_count,
                "active_users_trend": active_trend,
                "clinicians_count": clinician_count,
                "clinicians_trend": clinician_trend,
                "facility_admins_count": admin_count,
                "facility_admins_trend": admin_trend,
                "total_referrals_30d": total_referrals,
                "total_referrals_trend": referral_trend,
                "sent_referrals_30d": sent_referrals,
                "received_referrals_30d": received_referrals,
                "total_documents": total_documents,
                "total_documents_trend": doc_trend,
                "active_referrals": active_referrals,
                "pending_referrals": pending_referrals,
                "facility_utilization_percent": min(
                    round((total_referrals / 100) * 100, 1),
                    100
                ),
            }
        else:
            # User without facility
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )

    except Exception as e:
        logger.exception(f"Error in get_dashboard_kpis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving dashboard KPIs"
        )


@router.get("/referrals/by-status")
def get_referrals_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referrals grouped by status for pie chart visualization.
    
    Only shows key workflow statuses: submitted, accepted, in_transit, completed.
    """
    try:
        query = db.query(Referral)
        
        if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
            query = query.filter(
                or_(
                    Referral.from_facility_id == current_user.facility_id,
                    Referral.to_facility_id == current_user.facility_id,
                )
            )
        elif current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
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
        for ref_status in display_statuses:
            count = query.filter(Referral.status == ref_status.value).count()
            if count > 0:
                display_name = status_display_map.get(ref_status.value, ref_status.value)
                status_counts[display_name] = count
        
        return {
            "labels": list(status_counts.keys()),
            "data": list(status_counts.values()),
            "total": sum(status_counts.values()),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_referrals_by_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving referrals by status"
        )


@router.get("/referrals/by-priority")
def get_referrals_by_priority(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referrals grouped by priority for chart visualization."""
    try:
        query = db.query(Referral)
        
        if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
            query = query.filter(
                or_(
                    Referral.from_facility_id == current_user.facility_id,
                    Referral.to_facility_id == current_user.facility_id,
                )
            )
        elif current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_referrals_by_priority: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving referrals by priority"
        )


@router.get("/referrals/trend")
def get_referral_trend(
    days: int = Query(30, ge=7, le=90, description="Number of days for trend analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referral trend over time for line chart visualization."""
    try:
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
        
        if current_user.role != UserRole.SUPER_ADMIN and not current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )
        
        # Group by date using database aggregation
        daily_counts = {}
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_counts[date] = 0
        
        # Query aggregated daily counts
        daily_data = db.query(
            func.date(Referral.created_at).label("date"),
            func.count(Referral.id).label("count")
        ).filter(
            and_(
                Referral.created_at >= start_date,
                Referral.created_at <= end_date
            )
        )
        
        if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
            daily_data = daily_data.filter(
                or_(
                    Referral.from_facility_id == current_user.facility_id,
                    Referral.to_facility_id == current_user.facility_id,
                )
            )
        
        for date, count in daily_data.group_by(func.date(Referral.created_at)).all():
            date_str = date.strftime("%Y-%m-%d")
            if date_str in daily_counts:
                daily_counts[date_str] = count
        
        return {
            "labels": list(daily_counts.keys()),
            "data": list(daily_counts.values()),
            "total": sum(daily_counts.values()),
            "average_per_day": round(sum(daily_counts.values()) / max(days, 1), 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_referral_trend: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving referral trend"
        )


@router.get("/facilities/top-referring")
def get_top_referring_facilities(
    limit: int = Query(10, ge=1, le=50, description="Number of facilities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get top referring facilities for bar chart visualization."""
    try:
        # Only super admin can see all facilities
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can view this analytics"
            )
    
        # Count referrals by from_facility using aggregation
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
    except Exception as e:
        logger.error(f"Error in get_top_referring_facilities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving facility analytics"
        )


@router.get("/system-activity")
def get_system_activity_trend(
    months: int = Query(6, ge=1, le=12, description="Number of months for trend analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get system activity trend over months for combined chart visualization."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        # Initialize base queries
        patient_query = db.query(Patient)
        referral_query = db.query(Referral)
        document_query = db.query(ReferralDocument)

        if current_user.role != UserRole.SUPER_ADMIN and not current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )

        if current_user.role != UserRole.SUPER_ADMIN:
            facility_id = current_user.facility_id
            referral_query = referral_query.filter(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id,
                )
            )

            # Filter patients by facility
            patient_query = patient_query.join(PatientIdentifier).filter(
                PatientIdentifier.facility_id == facility_id
            )

            # Corrected subquery for referral IDs
            referral_ids = db.query(Referral.id).filter(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id,
                )
            ).subquery()
            document_query = document_query.filter(ReferralDocument.referral_id.in_(referral_ids))
        
        # Get monthly data for the specified period
        monthly_data = []
        for i in range(months, 0, -1):
            month_start = end_date - timedelta(days=i * 30)
            month_end = end_date - timedelta(days=(i - 1) * 30)
            
            month_label = month_start.strftime("%b")
            
            # Count using database aggregation
            patients_count = patient_query.filter(
                Patient.created_at >= month_start,
                Patient.created_at < month_end,
            ).count()
            
            referrals_count = referral_query.filter(
                Referral.created_at >= month_start,
                Referral.created_at < month_end,
            ).count()
            
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_system_activity_trend: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system activity trend"
        )


@router.get("/referrals/volume")
def get_referral_volume(
    months: int = Query(6, ge=1, le=12, description="Number of months for volume analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referral volume by month (incoming vs outgoing) for bar chart visualization."""
    try:
        if current_user.role != UserRole.SUPER_ADMIN and not current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )
        
        end_date = datetime.utcnow()
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_referral_volume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving referral volume"
        )


@router.get("/referrals/turnaround-time")
def get_turnaround_time_trend(
    weeks: int = Query(4, ge=1, le=12, description="Number of weeks for trend analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get average turnaround time by week for line chart visualization."""
    try:
        if current_user.role != UserRole.SUPER_ADMIN and not current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )
        
        end_date = datetime.utcnow()
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
            
            # Get average turnaround using database aggregation
            avg_turnaround = db.query(
                func.avg(
                    case(
                        (
                            and_(
                                Referral.updated_at.isnot(None),
                                Referral.created_at.isnot(None)
                            ),
                            extract('epoch', Referral.updated_at - Referral.created_at) / 86400
                        ),
                        else_=None
                    )
                )
            ).filter(
                Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
                Referral.created_at >= week_start,
                Referral.created_at < week_end,
            ).scalar() or 0
            
            weekly_data.append({
                "week": week_label,
                "days": round(avg_turnaround, 1),
            })
        
        return {
            "data": weekly_data,
            "period_weeks": weeks,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_turnaround_time_trend: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving turnaround time trend"
        )


@router.get("/referrals/by-reason")
def get_referrals_by_reason(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get referrals grouped by reason for chart visualization."""
    try:
        if current_user.role != UserRole.SUPER_ADMIN and not current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a facility"
            )
        
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
        
        # Group by reason using database aggregation to avoid loading all referrals into memory
        reason_counts = (
            db.query(
                Referral.reason_for_referral,
                func.count(Referral.id).label("count")
            )
            .group_by(Referral.reason_for_referral)
            .order_by(func.count(Referral.id).desc())
            .limit(10)
            .all()
        )
        
        return {
            "labels": [r[0] or "Not Specified" for r in reason_counts],
            "data": [r[1] for r in reason_counts],
            "total": sum(r[1] for r in reason_counts),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_referrals_by_reason: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving referrals by reason"
        )


@router.get("/facilities/performance")
def get_facility_performance(
    limit: int = Query(10, ge=1, le=50, description="Number of facilities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get facility performance metrics for chart visualization. Only for super admin."""
    try:
        # Only super admin can see all facilities
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can view this analytics"
            )
        
        # Get facility performance metrics in a single grouped query to eliminate the N+1 problem
        performance_query = (
            db.query(
                Facility.name.label("facility_name"),
                func.count(Referral.id).label("total_referrals"),
                func.sum(
                    case(
                        (Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]), 1),
                        else_=0
                    )
                ).label("completed_referrals"),
                func.avg(
                    case(
                        (
                            and_(
                                Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
                                Referral.updated_at.isnot(None),
                                Referral.created_at.isnot(None)
                            ),
                            extract('epoch', Referral.updated_at - Referral.created_at) / 86400
                        ),
                        else_=None
                    )
                ).label("avg_turnaround_days")
            )
            .join(Referral, Facility.id == Referral.from_facility_id, isouter=True)
            .group_by(Facility.id, Facility.name)
            .order_by(func.count(Referral.id).desc())
            .limit(limit)
        )

        performance_data = []
        for row in performance_query.all():
            total_referrals = row.total_referrals or 0
            completed_referrals = row.completed_referrals or 0
            avg_turnaround = round(row.avg_turnaround_days or 0, 1)
            completion_rate = round((completed_referrals / max(total_referrals, 1)) * 100, 1)
            
            performance_data.append({
                "facility": row.facility_name,
                "total_referrals": total_referrals,
                "completed_referrals": completed_referrals,
                "completion_rate": completion_rate,
                "avg_turnaround_days": avg_turnaround,
            })
        
        return {
            "data": performance_data,
            "total_facilities": len(performance_data),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_facility_performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving facility performance"
        )


@router.get("/system-health")
def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get system health metrics. Only accessible by super admin."""
    try:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can view system health"
            )
        
        # Calculate system health based on various metrics
        last_7_days = datetime.utcnow() - timedelta(days=7)
        
        # Get recent referral success rate using aggregation
        referral_stats = db.query(
            func.count(Referral.id).label("total"),
            func.sum(
                case(
                    (Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]), 1),
                    else_=0
                )
            ).label("completed"),
            func.sum(
                case(
                    (Referral.status == ReferralStatus.REJECTED.value, 1),
                    else_=0
                )
            ).label("rejected")
        ).filter(
            Referral.created_at >= last_7_days
        ).first()
        
        total = referral_stats.total or 0
        completed = referral_stats.completed or 0
        rejected = referral_stats.rejected or 0
        success_rate = (completed / max(total, 1)) * 100
        
        # Get facility metrics
        total_facilities = db.query(func.count(Facility.id)).scalar() or 0
        active_facilities = db.query(func.count(Facility.id)).filter(Facility.is_active == True).scalar() or 0
        facility_rate = (active_facilities / max(total_facilities, 1)) * 100
        
        # Get user metrics
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        user_rate = (active_users / max(total_users, 1)) * 100
        
        # Calculate overall health score
        health_score = round(
            (success_rate * 0.4) + (facility_rate * 0.3) + (user_rate * 0.3),
            1
        )
        
        uptime = 99.9
        error_rate = round((rejected / max(total, 1)) * 100, 1)
        avg_response_time = 245
        
        return {
            "healthScore": health_score,
            "uptime": uptime,
            "errorRate": error_rate,
            "avgResponseTime": avg_response_time,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_system_health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system health"
        )


@router.get("/api-requests")
def get_api_requests(
    days: int = Query(1, ge=1, le=30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get API request statistics. Only accessible by super admin."""
    try:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can view API request statistics"
            )

        service = get_analytics_service(db)
        return service.get_real_api_request_count(days=days)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_api_requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving API request statistics"
        )


@router.get("/metrics")
def get_analytics_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get overall analytics metrics for the system or facility with trend comparisons."""
    try:
        if current_user.role != UserRole.SUPER_ADMIN:
            if not current_user.facility_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not assigned to a facility"
                )
        
        # Build base queries based on user role
        if current_user.role == UserRole.SUPER_ADMIN:
            patient_query = db.query(Patient)
            referral_query = db.query(Referral)
            document_query = db.query(ReferralDocument)
        else:
            facility_id = current_user.facility_id
            referral_query = db.query(Referral).filter(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id,
                )
            )
            # Filter patients by facility only
            patient_query = db.query(Patient).join(PatientIdentifier).filter(
                PatientIdentifier.facility_id == facility_id
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
            document_query = db.query(ReferralDocument).filter(
                ReferralDocument.referral_id.in_(referral_ids)
            )
        
        total_patients = patient_query.count()
        total_referrals = referral_query.count()
        total_documents = document_query.count()
        
        # Count active users
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        
        # Calculate growth rate using aggregation
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        previous_30_days = last_30_days - timedelta(days=30)
        
        recent_referrals_count = referral_query.filter(
            Referral.created_at >= last_30_days
        ).count()
        previous_referrals_count = referral_query.filter(
            and_(
                Referral.created_at >= previous_30_days,
                Referral.created_at < last_30_days
            )
        ).count()
        
        growth_rate = 0
        if previous_referrals_count > 0:
            growth_rate = round(((recent_referrals_count - previous_referrals_count) / previous_referrals_count) * 100, 1)
        
        # Calculate turnaround time trend using aggregation
        recent_avg_turnaround = db.query(
            func.avg(
                case(
                    (
                        and_(
                            Referral.updated_at.isnot(None),
                            Referral.created_at.isnot(None)
                        ),
                        extract('epoch', Referral.updated_at - Referral.created_at) / 86400
                    ),
                    else_=None
                )
            )
        ).filter(
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
            Referral.created_at >= last_30_days
        ).scalar() or 0
        
        previous_avg_turnaround = db.query(
            func.avg(
                case(
                    (
                        and_(
                            Referral.updated_at.isnot(None),
                            Referral.created_at.isnot(None)
                        ),
                        extract('epoch', Referral.updated_at - Referral.created_at) / 86400
                    ),
                    else_=None
                )
            )
        ).filter(
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
            Referral.created_at >= previous_30_days,
            Referral.created_at < last_30_days
        ).scalar() or 0
        
        turnaround_trend = 0
        if previous_avg_turnaround > 0:
            turnaround_trend = round(((recent_avg_turnaround - previous_avg_turnaround) / previous_avg_turnaround) * 100, 1)
        
        # Calculate completion rate using aggregation
        recent_total = referral_query.filter(
            Referral.created_at >= last_30_days
        ).count()
        recent_completed_count = referral_query.filter(
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
            Referral.created_at >= last_30_days
        ).count()
        recent_completion_rate = (recent_completed_count / max(recent_total, 1)) * 100
        
        previous_total = referral_query.filter(
            and_(
                Referral.created_at >= previous_30_days,
                Referral.created_at < last_30_days
            )
        ).count()
        previous_completed_count = referral_query.filter(
            Referral.status.in_([ReferralStatus.COMPLETED.value, ReferralStatus.ACCEPTED.value]),
            Referral.created_at >= previous_30_days,
            Referral.created_at < last_30_days
        ).count()
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
            "turnaroundTrend": turnaround_trend,
            "completionRateTrend": completion_rate_trend,
            "pendingTrend": pending_trend,
            "recentAvgTurnaround": round(recent_avg_turnaround, 1),
            "recentCompletionRate": round(recent_completion_rate, 1),
            "recentPending": recent_pending,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analytics_metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving analytics metrics"
        )
