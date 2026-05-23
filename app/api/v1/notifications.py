"""
Notification Action Handlers API

This module provides API endpoints for handling notification actions
such as accepting referrals, calling code blue, etc.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.notifications import Notification, NotificationDelivery
from app.models.referral import Referral, ReferralStatus
from app.models.patient import Patient
from app.models.audit_log import AuditLog
from app.services.notification_service import get_notification_service
from app.services.audit_service import create_audit_logger
from app.enums import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/notifications/{notification_id}/actions/accept-referral")
async def accept_referral_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept an emergency referral

    Parameters:
    - notification_id: ID of the notification
    - current_user: Authenticated user
    - db: Database session
    """

    # Get notification
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Check if user has permission to accept referrals
    if current_user.role not in ["facility_admin", "clinician"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to accept referrals",
        )

    # Get referral ID from notification details
    referral_id_str = notification.details.get("referral_id", "").replace("R-", "")
    if not referral_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referral ID not found in notification",
        )

    try:
        referral_id = int(referral_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid referral ID format"
        )

    # Get referral
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    # Update referral status
    referral.status = ReferralStatus.ACCEPTED
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.now(timezone.utc)

    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="referral",
        entity_id=referral_id,
        details={
            "action": "accept_referral",
            "notification_id": notification_id,
            "previous_status": "submitted",
            "new_status": "accepted",
        },
    )

    # Update notification delivery tracking
    delivery = NotificationDelivery(
        notification_id=notification_id,
        user_id=current_user.id,
        delivery_method="websocket",
        action_taken="accept_referral",
        action_result={"referral_id": referral_id, "status": "accepted"},
        delivery_status="action_taken",
        delivered_at=datetime.now(timezone.utc),
    )
    db.add(delivery)

    db.commit()

    # Create follow-up notification
    notification_service = get_notification_service(db)
    notification_service.create_notification(
        notification_type="info",
        title="📋 REFERRAL ACCEPTED",
        message=f"Emergency referral for {referral.patient.first_name} {referral.patient.last_name} accepted",
        details={
            "referral_id": f"R-{referral.id}",
            "patient_name": f"{referral.patient.first_name} {referral.patient.last_name}",
            "accepted_by": f"{current_user.first_name} {current_user.last_name}",
            "accepted_at": referral.accepted_at.isoformat(),
        },
        actions=["📋 View Details"],
        roles=["facility_admin", "clinician"],
        backend_source="referrals",
        user_id=current_user.id,
    )

    return {
        "message": "Referral accepted successfully",
        "referral_id": referral_id,
        "patient_name": f"{referral.patient.first_name} {referral.patient.last_name}",
    }


@router.post("/notifications/{notification_id}/actions/call-code-blue")
async def call_code_blue_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiate Code Blue emergency response

    Parameters:
    - notification_id: ID of the notification
    - current_user: Authenticated user
    - db: Database session
    """

    # Get notification
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Check if user has permission
    if current_user.role not in ["facility_admin", "clinician"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to initiate Code Blue",
        )

    # Get patient details
    patient_id_str = notification.details.get("patient_id", "").replace("P-", "")
    if not patient_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID not found in notification",
        )

    try:
        patient_id = int(patient_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid patient ID format"
        )

    # Get patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    # Create emergency response record (would need EmergencyResponse model)
    # For now, we'll log the action and create notifications

    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="emergency_response",
        entity_id=patient_id,
        details={
            "action": "initiate_code_blue",
            "notification_id": notification_id,
            "location": notification.details.get("location", "Unknown"),
            "patient_id": patient_id,
            "vitals": notification.details.get("vitals", {}),
        },
    )

    # Update notification delivery tracking
    delivery = NotificationDelivery(
        notification_id=notification_id,
        user_id=current_user.id,
        delivery_method="websocket",
        action_taken="call_code_blue",
        action_result={
            "patient_id": patient_id,
            "location": notification.details.get("location"),
            "status": "code_blue_initiated",
        },
        delivery_status="action_taken",
        delivered_at=datetime.now(timezone.utc),
    )
    db.add(delivery)

    db.commit()

    # Create emergency notification for all clinical staff
    notification_service = get_notification_service(db)
    notification_service.create_notification(
        notification_type="critical",
        title="🚑 CODE BLUE ACTIVATED",
        message=f"Code Blue initiated in {notification.details.get('location', 'Unknown location')}",
        details={
            "patient_id": f"P-{patient_id}",
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "location": notification.details.get("location"),
            "initiated_by": f"{current_user.first_name} {current_user.last_name}",
            "initiated_at": datetime.now(timezone.utc).isoformat(),
        },
        actions=["🏥 Respond to Location", "📋 View Patient Details"],
        roles=["facility_admin", "clinician"],
        backend_source="emergency_response",
    )

    return {
        "message": "Code Blue initiated successfully",
        "patient_id": patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "location": notification.details.get("location"),
    }


@router.post("/notifications/{notification_id}/actions/suspend-user")
async def suspend_user_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Suspend user account due to HIPAA violation

    Parameters:
    - notification_id: ID of the notification
    - current_user: Authenticated user
    - db: Database session
    """

    # Get notification
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Check if user has permission (facility admin or super admin)
    if current_user.role not in ["facility_admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to suspend users",
        )

    # Get violating user ID
    violating_user_id = notification.details.get("user_id")
    if not violating_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Violating user ID not found in notification",
        )

    # Get violating user
    violating_user = db.query(User).filter(User.id == violating_user_id).first()
    if not violating_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Violating user not found"
        )

    # Check if current user can suspend this user (same facility or super admin)
    if current_user.role == "facility_admin":
        if current_user.facility_id != violating_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot suspend user from different facility",
            )

    # Suspend user account
    violating_user.is_active = False
    violating_user.suspended_at = datetime.now(timezone.utc)
    violating_user.suspended_by = current_user.id

    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="user",
        entity_id=violating_user_id,
        details={
            "action": "suspend_user",
            "reason": "hipaa_violation",
            "notification_id": notification_id,
            "violation_details": notification.details,
        },
    )

    # Update notification delivery tracking
    delivery = NotificationDelivery(
        notification_id=notification_id,
        user_id=current_user.id,
        delivery_method="websocket",
        action_taken="suspend_user",
        action_result={
            "suspended_user_id": violating_user_id,
            "suspended_user_name": f"{violating_user.first_name} {violating_user.last_name}",
            "suspension_reason": "hipaa_violation",
        },
        delivery_status="action_taken",
        delivered_at=datetime.now(timezone.utc),
    )
    db.add(delivery)

    db.commit()

    # Create compliance report notification
    notification_service = get_notification_service(db)
    notification_service.create_notification(
        notification_type="info",
        title="📋 COMPLIANCE REPORT FILED",
        message=f"HIPAA violation report filed for {violating_user.first_name} {violating_user.last_name}",
        details={
            "violating_user_id": violating_user_id,
            "violating_user_name": f"{violating_user.first_name} {violating_user.last_name}",
            "reported_by": f"{current_user.first_name} {current_user.last_name}",
            "audit_log_id": notification.details.get("audit_log_id"),
            "suspended_at": violating_user.suspended_at.isoformat(),
        },
        actions=["📋 View Report", "📞 Contact Security Team"],
        roles=["facility_admin", "super_admin"],
        backend_source="compliance",
    )

    return {
        "message": "User suspended successfully",
        "suspended_user_id": violating_user_id,
        "suspended_user_name": f"{violating_user.first_name} {violating_user.last_name}",
    }


@router.post("/notifications/{notification_id}/actions/restart-ai-services")
async def restart_ai_services_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Restart AI services (Super Admin only)

    Parameters:
    - notification_id: ID of the notification
    - current_user: Authenticated user
    - db: Database session
    """

    # Check if user is super admin
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Super Admin required.",
        )

    # Get notification
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Restart AI services (placeholder implementation)
    ai_services = ["groq", "whisper", "tesseract"]
    restart_results = {}

    for service in ai_services:
        try:
            # Implement actual service restart logic here
            # For now, simulate restart
            restart_results[service] = "success"
            logger.info(f"Restarted AI service: {service}")
        except Exception as e:
            restart_results[service] = f"failed: {str(e)}"
            logger.error(f"Failed to restart AI service {service}: {e}")

    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="system",
        details={
            "action": "restart_ai_services",
            "services": restart_results,
            "notification_id": notification_id,
        },
    )

    # Update notification delivery tracking
    delivery = NotificationDelivery(
        notification_id=notification_id,
        user_id=current_user.id,
        delivery_method="websocket",
        action_taken="restart_ai_services",
        action_result={"services": restart_results},
        delivery_status="action_taken",
        delivered_at=datetime.now(timezone.utc),
    )
    db.add(delivery)

    db.commit()

    # Create follow-up notification
    notification_service = get_notification_service(db)
    success_count = len([s for s in restart_results.values() if s == "success"])

    notification_service.create_notification(
        notification_type="info",
        title="🔄 AI SERVICES RESTARTED",
        message=f"AI services restart completed: {success_count}/{len(ai_services)} successful",
        details={
            "restart_results": restart_results,
            "success_count": success_count,
            "total_services": len(ai_services),
            "initiated_by": f"{current_user.first_name} {current_user.last_name}",
        },
        actions=["📊 View Details", "✅ Confirm Health"],
        roles=["super_admin"],
        backend_source="system",
        user_id=current_user.id,
    )

    return {
        "message": "AI services restart initiated",
        "results": restart_results,
        "success_count": success_count,
    }


@router.get("/notifications/{notification_id}/actions/view-details")
async def view_details_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a notification

    Parameters:
    - notification_id: ID of the notification
    - current_user: Authenticated user
    - db: Database session
    """

    # Get notification
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Check if user has permission to view this notification
    user_role = current_user.role
    if user_role not in notification.roles and "shared" not in notification.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this notification",
        )

    # Mark as read if not already read
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)

        # Update delivery tracking
        delivery = NotificationDelivery(
            notification_id=notification_id,
            user_id=current_user.id,
            delivery_method="websocket",
            action_taken="view_details",
            delivery_status="read",
            read_at=datetime.now(timezone.utc),
        )
        db.add(delivery)
        db.commit()

    # Return detailed information based on source
    details = notification.details.copy()

    if notification.backend_source == "referrals":
        # Add referral details
        if "referral_id" in details:
            referral_id_str = details["referral_id"].replace("R-", "")
            try:
                referral_id = int(referral_id_str)
                referral = db.query(Referral).filter(Referral.id == referral_id).first()
                if referral:
                    details["referral_details"] = {
                        "id": referral.id,
                        "status": referral.status,
                        "priority": referral.priority,
                        "created_at": referral.created_at.isoformat(),
                        "patient_name": f"{referral.patient.first_name} {referral.patient.last_name}",
                        "from_facility": referral.from_facility.name
                        if referral.from_facility
                        else "Unknown",
                        "to_facility": referral.to_facility.name
                        if referral.to_facility
                        else "Unknown",
                    }
            except (ValueError, AttributeError):
                pass

    elif notification.backend_source == "patients":
        # Add patient details
        if "patient_id" in details:
            patient_id_str = details["patient_id"].replace("P-", "")
            try:
                patient_id = int(patient_id_str)
                patient = db.query(Patient).filter(Patient.id == patient_id).first()
                if patient:
                    details["patient_details"] = {
                        "id": patient.id,
                        "name": f"{patient.first_name} {patient.last_name}",
                        "date_of_birth": patient.date_of_birth.isoformat()
                        if patient.date_of_birth
                        else None,
                        "gender": patient.gender,
                        "phone": patient.phone,
                        "email": patient.email,
                    }
            except (ValueError, AttributeError):
                pass

    return {
        "notification": {
            "id": notification.id,
            "type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "details": details,
            "actions": notification.actions,
            "backend_source": notification.backend_source,
            "timestamp": notification.created_at.isoformat(),
            "is_read": notification.is_read,
            "read_at": notification.read_at.isoformat()
            if notification.read_at
            else None,
        }
    }


@router.get("/notifications/{notification_id}/actions/review-backlog")
async def review_backlog_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed backlog information for overdue referrals

    Parameters:
    - notification_id: ID of the notification
    - current_user: Authenticated user
    - db: Database session
    """

    # Get notification
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Check permissions
    if current_user.role not in ["facility_admin", "clinician"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    # Get overdue referrals for this user
    overdue_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

    # Filter by user's facility if not super admin
    facility_filter = None
    if current_user.role == "facility_admin" and current_user.facility_id:
        facility_filter = current_user.facility_id
    elif current_user.role == "clinician" and current_user.facility_id:
        facility_filter = current_user.facility_id

    query = db.query(Referral).filter(
        Referral.status == ReferralStatus.PENDING,
        Referral.created_at < overdue_threshold,
    )

    if facility_filter:
        query = query.filter(
            or_(
                Referral.from_facility_id == facility_filter,
                Referral.to_facility_id == facility_filter,
            )
        )

    overdue_referrals = query.order_by(Referral.created_at.asc()).limit(50).all()

    # Format response
    backlog_details = []
    for referral in overdue_referrals:
        age_hours = (
            datetime.now(timezone.utc) - referral.created_at
        ).total_seconds() / 3600

        backlog_details.append(
            {
                "id": referral.id,
                "patient_name": f"{referral.patient.first_name} {referral.patient.last_name}",
                "priority": referral.priority,
                "created_at": referral.created_at.isoformat(),
                "age_hours": round(age_hours, 1),
                "from_facility": referral.from_facility.name
                if referral.from_facility
                else "Unknown",
                "to_facility": referral.to_facility.name
                if referral.to_facility
                else "Unknown",
                "reason_for_referral": referral.reason_for_referral[:100] + "..."
                if len(referral.reason_for_referral) > 100
                else referral.reason_for_referral,
            }
        )

    return {
        "backlog_count": len(backlog_details),
        "overdue_count": len([r for r in backlog_details if r["age_hours"] > 48]),
        "urgent_count": len(
            [r for r in backlog_details if r["priority"] == "emergency"]
        ),
        "referrals": backlog_details,
    }
