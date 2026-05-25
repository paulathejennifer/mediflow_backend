# MediFlow Comprehensive Notifications Flow Implementation Guide

## Overview

This document defines the complete notifications system for MediFlow with 50+ event types across three user roles. The system uses WebSocket for real-time notifications with database persistence for offline delivery.

---

## PART 1: NOTIFICATION EVENT TYPES BY ROLE

### A. SUPER_ADMIN NOTIFICATIONS (9 events)

Super admins monitor system health, facility management, and compliance.

| Event ID | Event Name | Trigger | Recipients | Details Required | Actions Available | Persistence |
|---|---|---|---|---|---|---|
| SA001 | Facility Created | New facility added to system | super_admin | facility_id, name, type, location, created_by, timestamp | View Facility, Send Welcome, Configure Settings | 24 hours |
| SA002 | Facility Status Changed | Facility activated/deactivated | super_admin | facility_id, name, old_status, new_status, reason, changed_by | Revert Change, Investigate, Archive |24 hours |
| SA003 | Facility Admin Assigned | New facility admin created | super_admin | user_id, name, email, facility_id, facility_name, permissions | Send Credentials, Configure Access, View Profile | 48 hours |
| SA004 | AI Service Down | AI service health check fails | super_admin | service_name, endpoint, error_msg, error_count, first_failure_time | Restart Service, View Logs, Check Monitoring | 4 hours |
| SA005 | Database Performance Alert | DB error rate > 10% | super_admin | error_rate, query_count, slow_queries, affected_operations, peak_time | Optimize DB, Check Connections, View Logs | 4 hours |
| SA006 | System Storage Critical | Total storage ≥ 90% | super_admin | used_storage, total_storage, growth_rate, days_until_full, largest_data_source | Cleanup Storage, Request Upgrade, Archive Data | 7 days |
| SA007 | Multiple Failed Logins | 5+ failed attempts from IP | super_admin | ip_address, attempted_usernames, attempt_count, time_window, locations | Block IP, Review Logs, Force Password Reset | 24 hours |
| SA008 | HIPAA Violation Detected | Unauthorized access attempt | super_admin | violating_user, accessed_patient_count, severity_level, record_types, timestamp | Suspend User, File Report, Notify Compliance | 30 days |
| SA009 | System Health Report | Daily/weekly health report | super_admin | uptime_percent, error_rate, active_facilities, active_users, key_metrics | View Full Report, Export, Configure Alerts | 7 days |

**Trigger Conditions:**
- SA001: New Facility record created
- SA002: Facility.is_active status changes
- SA003: User role = facility_admin created
- SA004: AI service health endpoint returns error 5+ times
- SA005: Database error rate calculated > 10% over 5-minute window
- SA006: Calculate total storage monthly
- SA007: Failed login attempts aggregated by IP
- SA008: Audit log with unauthorized_access = true or HIPAA violation detected
- SA009: Scheduled job runs daily at 8 AM

---

### B. FACILITY_ADMIN & CLINICIAN NOTIFICATIONS (20 events)

Both roles receive similar notifications with some differences. Facility Admins get additional management events.

#### B1: Shared Notifications (17 events)

| Event ID | Event Name | Trigger | Recipients | Details | Actions | Duration |
|---|---|---|---|---|---|---|
| FA001 | Incoming Referral | Patient referred to facility | facility_admin, clinician | patient_id, name, age, conditions, priority, from_facility, urgency_level, MRN, clinical_summary | Accept, Reject, Call Clinic, View Patient, Schedule Appointment | 7 days |
| FA002 | Referral Accepted | Referred patient accepted | facility_admin, clinician | patient_id, receiving_facility, accepting_physician_name, timestamp, ETA, accepting_facility_contact | Prepare Patient, Schedule Bed, Alert Staff, Update Family | 7 days |
| FA003 | Referral Rejected | Referral not accepted | facility_admin, clinician | patient_id, receiving_facility, rejection_reason, suggestions, next_steps | Contact Facility, Try Alternative, Escalate | 7 days |
| FA004 | Referral In Transit | Patient being transferred | facility_admin, clinician | patient_id, transport_method, ETA, location_updates, receiving_facility, transport_contact | Confirm Receipt, Update ETA, Alert Staff | 7 days |
| FA005 | Referral Received | Patient arrived at facility | facility_admin, clinician | patient_id, arrival_time, receiving_physician, ward_location, admission_status, vital_signs | Confirm Admission, Update Records, Notify Referring Clinic | 7 days |
| FA006 | Referral Completed | Care pathway finished | facility_admin, clinician | patient_id, discharge_date, outcomes, treatment_summary, follow_up_instructions, feedback_request | Provide Feedback, Close Case, Schedule Follow-up | 30 days |
| FA007 | Referral SLA Breached | Processing time > SLA | facility_admin, clinician | patient_id, time_elapsed, SLA_target, referral_id, current_step | Expedite, Escalate, Extend Timeline | 7 days |
| FA008 | Patient Documents Uploaded | New documents for patient | facility_admin, clinician | patient_id, document_type, uploader, file_count, file_size, file_names | Review, Analyze with AI, Download, Share | 7 days |
| FA009 | Test Results Available | Lab/Imaging results ready | facility_admin, clinician | patient_id, test_type, result_status (normal/abnormal/critical), results_summary, critical_findings | Review Results, Take Action, Contact Patient, Schedule Follow-up | 14 days |
| FA010 | Document Analysis Complete | AI OCR/analysis finished | facility_admin, clinician | document_id, document_name, extracted_data, confidence_percentage, actions_suggested, review_required | Review, Approve, Correct, Reject | 7 days |
| FA011 | Voice Note Transcribed | AI transcription complete | facility_admin, clinician | duration, transcription_length (words), accuracy_percent, confidence_score, key_findings, notes_preview | Review, Approve, Edit, Reject | 7 days |
| FA012 | Patient Follow-up Due | Patient needs follow-up | facility_admin, clinician | patient_id, days_since_referral, recommended_actions, contact_preferences, follow_up_type | Schedule Appointment, Send Message, Take Action | 3 days |
| FA013 | Unauthorized Access Attempt | Failed/suspicious access | facility_admin, clinician | user_id, accessed_patient_id, attempt_type, blocked_action, timestamp, ip_address | Review Logs, Take Action, Report | 24 hours |
| FA014 | Facility Announcement | Admin posts announcement | facility_admin, clinician | title, announcement_text, category, sender_name, urgency_level, required_actions | Read, Acknowledge, Take Action | 14 days |
| FA015 | Clinical Guideline Updated | New clinical guideline published | facility_admin, clinician | guideline_name, affected_conditions, affected_procedures, effective_date, summary, changes | Read Guideline, Acknowledge, Request Training | 30 days |
| FA016 | AI Performance Alert | AI accuracy < threshold | facility_admin, clinician | affected_services, accuracy_current, accuracy_target, impact_summary, affected_referrals | Review Quality, Escalate, Take Action | 7 days |
| FA017 | Weekly Performance Summary | Weekly performance report | facility_admin, clinician | referrals_created/received, completion_rate, avg_turnaround, patient_satisfaction_score, top_issues | View Full Report, Download, Share with Team | 7 days |

#### B2: Facility Admin Only (3 events)

| Event ID | Event Name | Trigger | Recipients | Details | Actions | Duration |
|---|---|---|---|---|---|---|
| FA101 | Clinician Created | New clinician added | facility_admin | user_id, name, email, specialization, facility_id, credentials | Send Welcome, Configure Access, Assign Patients | 48 hours |
| FA102 | Clinician Updated | Clinician profile/permissions changed | facility_admin | user_id, name, changed_fields, new_permissions, old_permissions, changed_by | Review Changes, Undo, Reassign Workload | 7 days |
| FA103 | Storage Warning (Facility) | Facility storage ≥ 80% | facility_admin | used_storage, total_storage, days_until_full, growth_rate, largest_data_source, recommendations | Cleanup, Archive, Request Upgrade | 7 days |

**Clinician Role Restrictions:**
- Clinicians cannot see FA101, FA102, FA103, SA*
- Clinicians cannot see system-wide metrics
- Clinicians see only their assigned patients/referrals
- Clinicians cannot create other users

---

### C. PATIENT NOTIFICATIONS (Optional Phase 2)

Future implementation - not in initial scope. Would include:
- Referral Status Updates
- Appointment Reminders
- Test Results Available
- Discharge Instructions

---

## PART 2: NOTIFICATION TRIGGERING SYSTEM

### Architecture

```
┌─────────────────────────────────────────────────────┐
│  Backend Event                                       │
│  (Create Referral, Update Status, AI Processing)    │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  Service Layer                                       │
│  notification_service.create_[event]_notification() │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  Notification Model                                  │
│  - Save to DB with metadata                          │
│  - Identify target users/roles/facilities           │
│  - Set expiration/priority                          │
└────────────────┬────────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
         ▼                ▼
    Connected         Offline
    WebSocket         Storage
         │                │
         └────────┬───────┘
                  │
                  ▼
         ┌─────────────────┐
         │   User/Role     │
         │   Broadcast     │
         └─────────────────┘
```

### Event-Triggered Notification Creators

#### 1. Referral Events

**Create → When new referral submitted:**
```python
# In referral_service.py
def create_referral(referral_data, current_user, db):
    referral = Referral(**referral_data)
    db.add(referral)
    db.commit()
    
    # Trigger notification
    notif_service = get_notification_service(db)
    if referral.priority == Priority.EMERGENCY:
        notif_service.create_incoming_referral_notification(
            referral,
            target_facility_id=referral.to_facility_id
        )
```

**Accept → When clinician accepts referral:**
```python
@router.patch("/referrals/{id}/accept")
def accept_referral(id, current_user, db):
    referral = db.query(Referral).get(id)
    referral.status = ReferralStatus.ACCEPTED
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.now()
    db.commit()
    
    notif_service = get_notification_service(db)
    notif_service.create_referral_accepted_notification(
        referral,
        target_facility_id=referral.from_facility_id  # Notify sender
    )
```

**Reject → When clinician rejects referral:**
```python
@router.patch("/referrals/{id}/reject")
def reject_referral(id, reason, current_user, db):
    referral = db.query(Referral).get(id)
    referral.status = ReferralStatus.REJECTED
    referral.rejection_reason = reason
    db.commit()
    
    notif_service = get_notification_service(db)
    notif_service.create_referral_rejected_notification(
        referral,
        reason=reason,
        target_facility_id=referral.from_facility_id
    )
```

**In Transit → When patient transported:**
```python
@router.patch("/referrals/{id}/in-transit")
def mark_in_transit(id, transport_details, current_user, db):
    referral = db.query(Referral).get(id)
    referral.status = ReferralStatus.IN_TRANSIT
    referral.transport_details = transport_details
    db.commit()
    
    notif_service = get_notification_service(db)
    notif_service.create_referral_in_transit_notification(
        referral,
        transport_details=transport_details,
        target_facility_id=referral.to_facility_id  # Notify receiver
    )
```

#### 2. Facility Events

**Create Facility:**
```python
@router.post("/facilities")
def create_facility(facility_data, current_user, db):
    facility = Facility(**facility_data)
    db.add(facility)
    db.commit()
    
    notif_service = get_notification_service(db)
    notif_service.create_facility_notification(
        facility,
        event_type="created",
        roles=["super_admin"]
    )
```

**Create Clinician:**
```python
@router.post("/users")
def create_user(user_data, current_user, db):
    user = User(**user_data)
    db.add(user)
    db.commit()
    
    if user.role in [UserRole.FACILITY_ADMIN, UserRole.CLINICIAN]:
        notif_service = get_notification_service(db)
        notif_service.create_user_notification(
            user,
            event_type="created",
            facility_id=current_user.facility_id,
            roles=["facility_admin"]
        )
```

#### 3. Document Events

**Upload Documents:**
```python
@router.post("/documents")
def upload_documents(files, referral_id, current_user, db):
    documents = []
    for file in files:
        doc = ReferralDocument(
            referral_id=referral_id,
            file_path=save_file(file),
            document_type=detect_type(file)
        )
        documents.append(doc)
    
    db.add_all(documents)
    db.commit()
    
    notif_service = get_notification_service(db)
    notif_service.create_document_uploaded_notification(
        referral_id=referral_id,
        document_count=len(documents),
        uploader_id=current_user.id
    )
```

#### 4. AI Processing Events

**Document Analysis Complete:**
```python
# In AI service callback (async)
def on_document_analysis_complete(document_id, results, db):
    doc = db.query(ReferralDocument).get(document_id)
    doc.ai_results = results
    doc.ai_status = AIStatus.COMPLETED
    db.commit()
    
    notif_service = get_notification_service(db)
    notif_service.create_document_analysis_notification(
        document_id=document_id,
        results=results,
        target_user_id=doc.referral.created_by_user_id
    )
```

---

## PART 3: WEBSOCKET CONNECTION & BROADCASTING

### WebSocket Endpoint

```python
# In app/api/v1/websocket.py
@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time notifications
    
    Usage from frontend:
    ws://backend/api/v1/websocket/notifications?token=JWT_TOKEN
    """
    
    # 1. Authenticate
    user = await authenticate_websocket(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # 2. Accept connection
    await connection_manager.connect(
        websocket=websocket,
        user_id=str(user.id),
        user_role=user.role,
        facility_id=user.facility_id,
    )
    
    # 3. Send pending notifications
    await connection_manager.send_pending_notifications(user.id)
    
    # 4. Keep connection alive
    while True:
        try:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
        except WebSocketDisconnect:
            break
    
    # 5. Cleanup
    await connection_manager.disconnect(str(user.id))
```

### Broadcasting Logic

```python
# In app/websocket/manager.py
class NotificationBroadcaster:
    async def broadcast_notification(self, notification: Notification, db: Session):
        """Broadcast to appropriate users"""
        
        notification_data = {...}  # Format as JSON
        
        # Route by target type
        if notification.user_id:
            # Direct to user
            await self.send_to_user(notification.user_id, notification_data)
        
        if notification.roles:
            # Broadcast to roles (super_admin, facility_admin, clinician)
            for role in notification.roles:
                await self.broadcast_to_role(role, notification_data)
        
        if notification.facility_id:
            # Broadcast to facility (all users in facility)
            await self.broadcast_to_facility(notification.facility_id, notification_data)
        
        # Store in DB for offline users
        delivery = NotificationDelivery(
            notification_id=notification.id,
            delivery_method="websocket",
            delivery_status="pending"
        )
        db.add(delivery)
        db.commit()
```

### Message Format (JSON over WebSocket)

```json
{
  "id": 12345,
  "type": "critical|warning|info",
  "title": "🚨 EMERGENCY REFERRAL",
  "message": "Cardiac patient requires immediate transfer",
  "details": {
    "patient_id": "P-456",
    "patient_name": "John Doe",
    "age": 45,
    "condition": "Acute MI",
    "urgency": "life-threatening",
    "referral_id": "R-789",
    "time_sensitive": "30 minutes",
    "from_facility": "City Hospital",
    "from_facility_contact": "+1234567890",
    "clinical_summary": "..."
  },
  "actions": [
    {"label": "Accept Referral", "id": "accept", "style": "primary"},
    {"label": "Contact Clinic", "id": "contact", "style": "secondary"}
  ],
  "roles": ["facility_admin", "clinician"],
  "backend_source": "referrals",
  "timestamp": "2026-05-25T14:30:00Z",
  "expires_at": "2026-05-25T15:30:00Z",
  "priority": "high"
}
```

---

## PART 4: DATABASE SCHEMA

### Notification Models

```python
# app/models/notifications.py

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)  # Direct recipient
    facility_id = Column(Integer, ForeignKey("facility.id"), nullable=True)  # Facility broadcast
    notification_type = Column(String(50))  # critical, warning, info
    title = Column(String(255))
    message = Column(Text)
    details = Column(JSON)  # Event-specific data
    actions = Column(JSON)  # Available actions
    roles = Column(JSON)  # ["super_admin"], ["facility_admin", "clinician"], etc
    backend_source = Column(String(50))  # referrals, facilities, users, ai, etc
    trigger_condition = Column(Text, nullable=True)  # Trigger logic for debugging
    priority = Column(String(20), default="normal")  # high, normal, low
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # When to stop delivering
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    
    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    delivery_method = Column(String(50))  # websocket, email, sms
    delivery_status = Column(String(50))  # pending, delivered, failed, read
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    delivery_attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    notification_type = Column(String(50))  # critical, warning, info, etc
    enabled = Column(Boolean, default=True)
    delivery_methods = Column(JSON)  # ["websocket", "email", "sms"]
    quiet_hours_start = Column(Time, nullable=True)  # 22:00
    quiet_hours_end = Column(Time, nullable=True)    # 08:00
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## PART 5: FRONTEND IMPLEMENTATION PATTERN

### React WebSocket Hook

```typescript
// hooks/useNotifications.ts
import { useEffect, useState, useCallback } from 'react';

interface Notification {
  id: number;
  type: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  details: Record<string, any>;
  actions: Array<{ label: string; id: string }>;
  timestamp: string;
}

export const useNotifications = (accessToken: string) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const token = accessToken;
    if (!token) return;

    const wsUrl = `wss://${process.env.REACT_APP_API_HOST}/api/v1/websocket/notifications?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      console.log('Connected to notifications');
    };

    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications(prev => [notification, ...prev]);
      
      // Show toast/sound alert for critical
      if (notification.type === 'critical') {
        playSound('alert.mp3');
        showToast(notification.title, notification.message);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Attempt reconnect after 5 seconds
      setTimeout(() => {
        // Reconnection logic
      }, 5000);
    };

    return () => {
      ws.close();
    };
  }, [accessToken]);

  const handleAction = useCallback((notificationId: number, actionId: string) => {
    // Send action to backend
    fetch(`/api/v1/notifications/${notificationId}/actions/${actionId}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
  }, [accessToken]);

  return { notifications, connected, handleAction };
};
```

### Usage in Component

```typescript
// components/NotificationCenter.tsx
export const NotificationCenter = () => {
  const { notifications, connected, handleAction } = useNotifications(accessToken);

  return (
    <div className="notification-center">
      <div className="connection-status">
        {connected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>
      
      <div className="notifications-list">
        {notifications.map(notif => (
          <NotificationCard
            key={notif.id}
            notification={notif}
            onAction={handleAction}
          />
        ))}
      </div>
    </div>
  );
};
```

---

## PART 6: IMPLEMENTATION ROADMAP

### Phase 1: Core Fixes (Completed)
- ✅ Replace error dicts with HTTPException
- ✅ Add facility validation (403 on null)
- ✅ Filter patient counts by facility
- ✅ Fix N+1 queries with aggregation
- ✅ Add try-except blocks

### Phase 2: Notification Services (Week 1-2)
- [ ] Create 50+ notification generator methods in NotificationService
- [ ] Add event triggers in all relevant services
- [ ] Implement notification scheduling/queuing
- [ ] Test WebSocket broadcasting

### Phase 3: Frontend Integration (Week 2-3)
- [ ] Implement WebSocket connection with auto-reconnect
- [ ] Build notification center UI component
- [ ] Add notification badges/counters
- [ ] Implement action handling
- [ ] Add notification preferences/settings

### Phase 4: Advanced Features (Week 3-4)
- [ ] Email fallback for critical notifications
- [ ] SMS for emergency referrals (optional)
- [ ] Notification digest emails
- [ ] Read receipts and delivery tracking
- [ ] Notification rules engine (custom filters)

### Phase 5: Testing & Optimization (Week 4-5)
- [ ] Load testing with 100+ concurrent connections
- [ ] Notification delivery guarantee testing
- [ ] Offline scenario testing
- [ ] Performance optimization
- [ ] Documentation & training

---

## PART 7: DEPLOYMENT CHECKLIST

- [ ] Database migrations for Notification* models
- [ ] Environment variables for notification settings
- [ ] WebSocket configuration for production
- [ ] Message queue setup (if using Celery)
- [ ] Email service configuration (if needed)
- [ ] Monitoring/alerting for notification failures
- [ ] Load testing before go-live
- [ ] Notification templates in multilingual support
- [ ] User onboarding for notification center
- [ ] Support documentation

---

## TESTING SCENARIOS

### Manual Testing

1. **Super Admin Receives Facility Creation Alert**
   - Create new facility via API
   - Super Admin should receive notification via WebSocket
   - Notification persists if offline

2. **Clinician Receives Incoming Referral**
   - Create referral to facility
   - Facility clinicians receive notification
   - Can accept/reject from notification action

3. **Offline Pending Notifications**
   - Disconnect WebSocket
   - Create referral
   - Reconnect WebSocket
   - Should receive pending notification

### Automated Testing

```python
# tests/test_notifications.py
def test_emergency_referral_notification(db, client):
    # Create emergency referral
    referral = create_referral(..., priority=Priority.EMERGENCY)
    
    # Check notification created
    notification = db.query(Notification).filter_by(
        backend_source="referrals",
        notification_type="critical"
    ).first()
    
    assert notification is not None
    assert "facility_admin" in notification.roles

def test_facility_validation_403(db, client):
    # Try to access analytics as facility user without facility_id
    response = client.get(
        "/api/v1/analytics/referrals",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
```

