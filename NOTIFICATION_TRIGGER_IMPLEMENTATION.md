# Notification Trigger Implementation Guide

## How to Add Notification Triggers

Notification triggers need to be added to the service layer where events occur. Below are the patterns and examples.

## Pattern 1: After Creating a Referral (FA001)

**File**: `app/services/referral_service.py`

```python
from app.services.notification_service import get_notification_service

@router.post("/referrals")
def create_referral(referral_data: ReferralSchema, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ... existing code to create referral ...
    
    referral = Referral(**referral_data)
    db.add(referral)
    db.commit()
    db.refresh(referral)
    
    # ✅ ADD NOTIFICATION TRIGGER
    if referral.priority == Priority.EMERGENCY.value:
        notif_service = get_notification_service(db)
        notif_service.create_incoming_referral_notification(referral)
    
    return referral
```

## Pattern 2: After Accepting a Referral (FA002)

**File**: `app/endpoints/referrals.py`

```python
@router.patch("/referrals/{referral_id}/accept")
def accept_referral(referral_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    referral = db.query(Referral).get(referral_id)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    referral.status = ReferralStatus.ACCEPTED.value
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.utcnow()
    db.commit()
    
    # ✅ ADD NOTIFICATION TRIGGER
    notif_service = get_notification_service(db)
    notif_service.create_referral_accepted_notification(
        referral,
        accepted_by_user=current_user
    )
    
    return referral
```

## Pattern 3: Status Changes with Async Notifications

For operations that might take time, queue notifications:

```python
@router.patch("/referrals/{referral_id}/status")
def update_referral_status(referral_id: int, new_status: str, db: Session = Depends(get_db)):
    referral = db.query(Referral).get(referral_id)
    old_status = referral.status
    referral.status = new_status
    db.commit()
    
    # ✅ TRIGGER APPROPRIATE NOTIFICATION
    notif_service = get_notification_service(db)
    
    if new_status == ReferralStatus.ACCEPTED.value:
        notif_service.create_referral_accepted_notification(referral, accepted_by_user=current_user)
    
    elif new_status == ReferralStatus.REJECTED.value:
        notif_service.create_referral_rejected_notification(referral, rejection_reason="Capacity exceeded")
    
    elif new_status == ReferralStatus.IN_TRANSIT.value:
        notif_service.create_referral_in_transit_notification(referral, transport_method="Ambulance")
    
    elif new_status == ReferralStatus.RECEIVED.value:
        notif_service.create_referral_received_notification(referral)
    
    elif new_status == ReferralStatus.COMPLETED.value:
        notif_service.create_referral_completed_notification(referral)
    
    return referral
```

## Where to Add Each Trigger

### Referral Service (`app/services/referral_service.py` or `app/endpoints/referrals.py`)
- FA001 - create_referral() → create_incoming_referral_notification()
- FA002 - accept_referral() → create_referral_accepted_notification()
- FA003 - reject_referral() → create_referral_rejected_notification()
- FA004 - mark_in_transit() → create_referral_in_transit_notification()
- FA005 - mark_received() → create_referral_received_notification()
- FA006 - complete_referral() → create_referral_completed_notification()
- FA007 - (Scheduled job) → monitor_referral_performance()

### Facility Service (`app/services/facility_service.py` or `app/endpoints/facilities.py`)
- SA001 - create_facility() → create_facility_created_notification()
- SA002 - update_facility_status() → create_facility_status_changed_notification()

### User Service (`app/endpoints/users.py`)
- SA003 - create_user() → create_facility_admin_assigned_notification()
- FA101 - create_clinician() → create_clinician_created_notification()
- FA102 - update_clinician() → create_clinician_updated_notification()

### Document Service (`app/endpoints/documents.py`)
- FA008 - upload_documents() → create_patient_documents_uploaded_notification()

### AI Service (`app/services/ai_service.py` or async callback)
- FA010 - on_document_analysis_complete() → create_document_analysis_complete_notification()
- FA011 - on_voice_transcription_complete() → create_voice_note_transcribed_notification()

### Patient Service (`app/services/patient_service.py`)
- FA009 - on_test_results_received() → create_test_results_notification()
- FA012 - (Scheduled job) → create_patient_followup_due_notification()

### Monitoring/Scheduled Jobs
- SA004 - health_check_monitor() → create_ai_service_down_notification()
- SA005 - db_performance_monitor() → create_database_performance_alert_notification()
- SA006 - storage_monitor() → create_storage_critical_notification()
- SA007 - login_attempts_monitor() → create_multiple_failed_logins_notification()
- SA009 - daily_health_report_job() → create_system_health_report_notification()
- FA013 - audit_log_monitor() → create_unauthorized_access_notification()
- FA014 - send_facility_announcement() → create_facility_announcement_notification()
- FA015 - publish_guideline() → create_clinical_guideline_updated_notification()
- FA016 - ai_quality_check() → create_ai_performance_alert_notification()
- FA017 - generate_weekly_report() → create_weekly_performance_summary_notification()
- FA103 - facility_storage_monitor() → create_storage_warning_notification()

## Example: Complete Referral Workflow

```python
# In app/endpoints/referrals.py

from app.services.notification_service import get_notification_service

@router.post("/referrals")
def submit_referral(
    referral_data: ReferralCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a new referral"""
    # Validate user has facility
    if not current_user.facility_id:
        raise HTTPException(status_code=403, detail="User not assigned to facility")
    
    # Create referral
    referral = Referral(
        **referral_data.dict(),
        from_facility_id=current_user.facility_id,
        created_by_user_id=current_user.id,
        status=ReferralStatus.SUBMITTED.value
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)
    
    # ✅ TRIGGER NOTIFICATION
    notif_service = get_notification_service(db)
    notif_service.create_incoming_referral_notification(referral)
    
    return referral


@router.patch("/referrals/{referral_id}/accept")
def accept_referral(
    referral_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept an incoming referral"""
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    if referral.status != ReferralStatus.SUBMITTED.value:
        raise HTTPException(status_code=400, detail="Can only accept submitted referrals")
    
    # Update referral
    referral.status = ReferralStatus.ACCEPTED.value
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.utcnow()
    db.commit()
    
    # ✅ TRIGGER NOTIFICATION
    notif_service = get_notification_service(db)
    notif_service.create_referral_accepted_notification(referral, current_user)
    
    return referral


@router.patch("/referrals/{referral_id}/reject")
def reject_referral(
    referral_id: int,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject an incoming referral"""
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    # Update referral
    referral.status = ReferralStatus.REJECTED.value
    referral.rejection_reason = reason
    db.commit()
    
    # ✅ TRIGGER NOTIFICATION
    notif_service = get_notification_service(db)
    notif_service.create_referral_rejected_notification(referral, reason)
    
    return referral


@router.patch("/referrals/{referral_id}/in-transit")
def mark_in_transit(
    referral_id: int,
    transport_details: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark referral as in transit"""
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    # Update referral
    referral.status = ReferralStatus.IN_TRANSIT.value
    referral.transport_details = transport_details
    db.commit()
    
    # ✅ TRIGGER NOTIFICATION
    notif_service = get_notification_service(db)
    notif_service.create_referral_in_transit_notification(
        referral,
        transport_method=transport_details.get("method", "Ambulance")
    )
    
    return referral


@router.patch("/referrals/{referral_id}/received")
def mark_received(
    referral_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark referral as received at destination"""
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    # Update referral
    referral.status = ReferralStatus.RECEIVED.value
    referral.received_at = datetime.utcnow()
    db.commit()
    
    # ✅ TRIGGER NOTIFICATION
    notif_service = get_notification_service(db)
    notif_service.create_referral_received_notification(referral)
    
    return referral


@router.patch("/referrals/{referral_id}/complete")
def complete_referral(
    referral_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark referral as completed"""
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    # Update referral
    referral.status = ReferralStatus.COMPLETED.value
    referral.completed_at = datetime.utcnow()
    db.commit()
    
    # ✅ TRIGGER NOTIFICATION
    notif_service = get_notification_service(db)
    notif_service.create_referral_completed_notification(referral)
    
    return referral
```

## Testing Notifications

### 1. WebSocket Connection Test
```bash
# Connect to WebSocket
ws://localhost:8000/api/v1/websocket/notifications?token=YOUR_JWT_TOKEN
```

### 2. Create Notification and Verify Delivery
```python
# In Python console
import requests

# Create referral (triggers FA001)
response = requests.post(
    'http://localhost:8000/api/v1/referrals',
    json={...referral_data...},
    headers={'Authorization': 'Bearer YOUR_JWT_TOKEN'}
)

# Check if notification was sent via WebSocket
```

### 3. Monitor Broadcast Results
Check logs for messages like:
```
Broadcast to roles ['facility_admin', 'clinician']: 5 sent, 0 failed
Notification sent to user 123
```

## Next Steps

1. Add triggers to referral endpoints ✅ (See example above)
2. Add triggers to facility endpoints
3. Add triggers to document endpoints
4. Add triggers to user management endpoints
5. Create scheduled jobs for monitoring (SA004-SA009, FA012, FA017)
6. Test end-to-end with frontend WebSocket client
7. Deploy to Render
