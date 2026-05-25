# MediFlow Dashboard/Analytics Issues & Comprehensive Notifications Plan

## PART 1: WHY DASHBOARD & ANALYTICS FETCH IS FAILING

### Summary
The frontend cannot fetch dashboard and analytics data for all three users because:
1. **Endpoints return HTTP 200 with error messages** instead of proper HTTP 401/403 status codes
2. **No facility validation** - users without assigned facilities get ALL system data instead of errors
3. **Data leakage** - patient counts show system-wide data, not filtered to user's facility
4. **N+1 query problems** - can cause 504 timeouts
5. **No exception handling** - crashes return 500 errors with stack traces

---

### Critical Issue #1: Wrong HTTP Status Codes

**What's happening:**
Some endpoints return an error object with HTTP 200 instead of proper error codes:

```python
# WRONG - This happens in several endpoints
if current_user.role != UserRole.SUPER_ADMIN:
    return {
        "error": "Only super admin...",  # Returns with HTTP 200!
        ...
    }

# CORRECT - What should happen
if current_user.role != UserRole.SUPER_ADMIN:
    raise HTTPException(status_code=403, detail="Only super admin...")
```

**Affected Endpoints:**
- `GET /analytics/system-health` 
- `GET /analytics/api-requests`
- `GET /analytics/facility-performance`
- `GET /analytics/top-referring-facilities`
- `GET /analytics/metrics`

**Why Frontend Can't Handle This:**
Frontend code likely checks:
```javascript
if (response.status !== 200) {
    // Show error
}
```

Since it gets 200, it doesn't recognize the error and tries to process invalid data.

---

### Critical Issue #2: Missing Facility Validation

**What's happening:**
```python
# Current code in get_analytics_metrics()
if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
    # Apply facility filter
    ...
# If facility_id is NULL, NO FILTER IS APPLIED!
# User gets system-wide data instead of error or no data
```

**Affected Endpoints:**
- `GET /analytics/referrals` - lines 36-50
- `GET /analytics/dashboard` - lines 206-230
- `GET /analytics/metrics` - lines 928+

**Impact:**
- Facility Admin with `facility_id = NULL` sees all patients, all referrals, all analytics for entire system
- Clinician with `facility_id = NULL` sees entire system (security issue + data leakage)

**Why It Happens:**
Comment in code says "facility isolation happens at service layer" but analytics queries don't use the service layer!

---

### Critical Issue #3: Data Leakage in Patient Counts

**What's happening:**
```python
# In get_dashboard_kpis()
total_patients = patient_query.join(
    # Assuming there's a relationship through patient_identifiers
).filter(
    # Filter by facility - adjust based on actual schema
).count()

# THEN immediately does:
total_patients = patient_query.count()  # ← Gets ALL patients!
```

**Impact:**
- Facility Admin sees total patient count for entire system
- Should only see patients from their facility
- Comment literally says "For simplicity, count all patients"

---

### Critical Issue #4: N+1 Query Problem (Performance)

**What's happening:**
```python
# In get_facility_performance()
for facility in facilities:  # Gets 10 facilities
    total_referrals = db.query(Referral).filter(...).count()  # Query 1
    completed_referrals = db.query(Referral).filter(...).count()  # Query 2
    completed_list = db.query(Referral).filter(...).all()  # Query 3
    # ... manual aggregation of times
```

**Impact:**
- 10 facilities × 3+ queries = 30+ database hits for ONE API call
- Can cause 504 Gateway Timeout
- Database connection pool exhaustion

---

### Critical Issue #5: Full Data Loads into Memory

**What's happening:**
```python
# In get_turnaround_time_trend()
for referral in referrals.all():  # Loads ALL referrals into memory
    # Manual aggregation in Python
```

**Impact:**
- 1000+ referrals loaded into Python memory
- Manual aggregation is slow (should use SQL aggregation)
- Can cause memory exhaustion on server

---

## PART 2: CURRENT NOTIFICATIONS SYSTEM

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (WebSocket Client)                            │
│  - Connects with JWT token                              │
│  - Receives notifications in real-time                  │
│  - Also polls GET /notifications for offline messages   │
└────────────────┬────────────────────────────────────────┘
                 │ WebSocket
                 │ ws://backend/websocket/notifications
                 │
┌────────────────▼────────────────────────────────────────┐
│  BACKEND WebSocket Manager                              │
│  - Tracks active connections by user_id, role, facility │
│  - Routes notifications to appropriate users            │
│  - Stores pending notifications for offline users       │
└────────────────▲────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────────────┐
│  Backend Event Triggers                                 │
│  - User creates referral                                │
│  - Facility admin creates clinician                     │
│  - System detects issues (AI down, storage warning)     │
│                                                          │
│  → notification_service.create_[event]_notification()   │
│  → Broadcaster sends via WebSocket or stores in DB      │
└─────────────────────────────────────────────────────────┘
```

### How Notifications Flow Works

**Step 1: Event Occurs in Backend**
```python
# Example: In referral_service.py when creating referral
referral = create_referral(...)
notification_service = get_notification_service(db)
notification_service.create_emergency_referral_notification(referral)
```

**Step 2: Notification Saved to Database**
```python
# In notification_service.py
def create_notification(
    notification_type="critical",
    title="🚨 EMERGENCY REFERRAL",
    message="...",
    details={...},
    actions=[...],
    roles=["facility_admin", "clinician"],  # Who receives it
    backend_source="referrals"
):
    notification = Notification(...)
    db.add(notification)
    db.commit()
    
    # Broadcast immediately via WebSocket
    asyncio.create_task(
        broadcaster.broadcast_notification(notification, db)
    )
```

**Step 3: Broadcaster Routes to Target Users**
```python
# In WebSocket Manager
async def broadcast_notification(self, notification: Notification, db: Session):
    if notification.user_id:  # Single user
        await self.send_to_user(notification.user_id, notification_data)
    
    if notification.roles:  # All users with certain roles
        await self.broadcast_to_roles(notification.roles, notification_data)
    
    if notification.facility_id:  # All users in facility
        await self.broadcast_to_facility(notification.facility_id, notification_data)
```

**Step 4: Send to Connected Users**
```python
# If user is connected via WebSocket
await websocket.send_text(json.dumps(notification_data))

# If user is offline
# Notification stored in DB, sent on next connection:
async def send_pending_notifications(self, user_id: int):
    pending = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).all()
    
    for notification in pending:
        await send_to_user(user_id, notification)
```

**Step 5: Frontend Receives**
```javascript
// Connection
const ws = new WebSocket(
  `wss://backend/api/v1/websocket/notifications?token=${jwtToken}`
);

// On message
ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log("New notification:", notification);
  // Update UI
};
```

---

## PART 3: CURRENT NOTIFICATION TYPES (9 types)

### 1. Emergency Referral
- **Type**: critical
- **Trigger**: Referral with priority='emergency'
- **Receivers**: Facility Admin, Clinician
- **Details**: Patient info, urgency, referring facility
- **Actions**: Accept Referral, Contact Referring MD

### 2. HIPAA Violation
- **Type**: critical
- **Trigger**: Unauthorized patient record access
- **Receivers**: Facility Admin, Clinician, + Super Admin
- **Details**: User ID, accessed records count, facility
- **Actions**: Suspend User, File Compliance Report

### 3. AI Service Down
- **Type**: critical
- **Trigger**: AI service unreachable
- **Receivers**: Super Admin only
- **Details**: Service name, endpoint, error count
- **Actions**: Restart Services, Check System Logs

### 4. Referral Processing Delays
- **Type**: warning
- **Trigger**: Average processing time > SLA × 1.5
- **Receivers**: Facility Admin, Clinician
- **Details**: SLA target, current avg, backlog count, departments
- **Actions**: Review Backlog, Reassign Staff

### 5. AI Performance Degrading
- **Type**: warning
- **Trigger**: AI accuracy < 90%
- **Receivers**: Facility Admin, Clinician
- **Details**: Current accuracy, minimum required, affected services
- **Actions**: Restart AI Services, View Analytics

### 6. Storage Warning
- **Type**: warning
- **Trigger**: Facility storage ≥ 85%
- **Receivers**: Facility Admin only
- **Details**: Used storage, total storage, days until full, growth rate
- **Actions**: Cleanup Storage, Request Upgrade

### 7. Referral Status Update
- **Type**: info
- **Trigger**: Referral status changes
- **Receivers**: Facility Admin, Clinician
- **Details**: Patient name, referral ID, accepting facility, physician
- **Actions**: View Details, Prepare Patient

### 8. Voice Note Transcribed
- **Type**: info
- **Trigger**: Voice note AI transcription complete
- **Receivers**: Facility Admin, Clinician
- **Details**: Recording duration, accuracy %, word count, processing time
- **Actions**: Review Transcript, Approve Note

### 9. Weekly Team Performance
- **Type**: info
- **Trigger**: Weekly report generation
- **Receivers**: Facility Admin only
- **Details**: Top performer, avg referral time, patient satisfaction, completion rate
- **Actions**: Recognize Team, View Details

---

## PART 4: COMPREHENSIVE NOTIFICATIONS FOR ALL THREE USERS

### A. SUPER_ADMIN NOTIFICATIONS (7 types)

System-wide monitoring and administrative tasks:

| # | Event | Trigger | Details Needed | Actions |
|---|-------|---------|----------------|---------| 
| 1 | **Facility Created** | Admin creates facility | Facility name, type, location | View Facility, Send Welcome |
| 2 | **Facility Status Changed** | Facility activated/deactivated | Facility name, old/new status | View Details, Manage Status |
| 3 | **Facility Admin Created** | New facility admin user created | User name, facility, email | Send Welcome, Configure Access |
| 4 | **Facility Deleted** | Facility removed from system | Facility name, reason, date | Confirm Deletion, View Archive |
| 5 | **AI Service Down** | Service health check fails | Service name, error details, since | Restart Service, Check Logs |
| 6 | **Database Performance Alert** | DB error rate > 10% or slow queries | Error %, affected queries, connections | Check Logs, Optimize DB |
| 7 | **System Storage Critical** | Total system storage ≥ 90% | Used/total storage, growth rate | Cleanup, Request Infrastructure |
| 8 | **Multiple Failed Logins** | 5+ failed attempts from IP | IP address, user attempts, time window | Block IP, Review Logs |
| 9 | **System Health Report** | Daily/Weekly report | Uptime %, error rates, performance | View Full Report, Export |

---

### B. FACILITY_ADMIN NOTIFICATIONS (20+ types)

Facility management + referral management + operational alerts:

#### Facility Management (4)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 1 | **Clinician Created** | Admin creates clinician | Clinician name, specialization, email | Send Welcome, Configure Access |
| 2 | **Clinician Updated** | Clinician profile/role changed | Changed fields, new permissions | View Changes, Undo |
| 3 | **Clinician Deactivated** | Clinician account disabled | Clinician name, reason, date | Reactivate, View Archive |
| 4 | **New Facility Admin Permission** | User promoted to facility admin | User name, facilities assigned | Configure Role, View Access |

#### Referral Management (8) - **CRITICAL FOR OPERATIONS**
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 5 | **Incoming Referral Received** | Patient referred to facility | Patient name, urgency, from facility, MRN, patient age/condition | Accept/Reject, Contact Clinic |
| 6 | **Outgoing Referral Accepted** | Referred patient accepted by facility | Patient name, receiving facility, accepting physician | Prepare Patient, Schedule |
| 7 | **Outgoing Referral Rejected** | Receiving facility rejected referral | Patient name, receiving facility, rejection reason | Contact Facility, Reassign |
| 8 | **Referral In Transit** | Patient being transferred | Patient name, transport, ETA, receiving facility | Prepare Beds, Alert Staff |
| 9 | **Referral Received** | Patient arrived at receiving facility | Patient name, receiving facility, admission time | Confirm Admission, Update Records |
| 10 | **Referral Completed** | Patient discharged/completed care | Patient name, discharge date, outcomes, feedback | Provide Feedback, Close Case |
| 11 | **Referral SLA Alert** | Referral processing taking too long | Patient name, time elapsed, SLA target | Expedite, Escalate |
| 12 | **Referral Requires Action** | Document missing, signature needed, etc | Patient name, action required, deadline | Take Action, View Details |

#### Patient Management (3)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 13 | **New Patient Registered** | Patient added to facility | Patient name, MRN, DOB, contact | View Profile, Schedule Appointment |
| 14 | **Patient Documents Uploaded** | New documents for patient | Patient name, document type, uploader | Review, OCR Analyze |
| 15 | **Test Results Available** | Lab/Imaging results ready | Patient name, test type, normal/abnormal, link to results | Review Results, Take Action |

#### AI Processing (2)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 16 | **Document Analysis Complete** | AI OCR/analysis done | Document name, analyzed fields, confidence %, actions suggested | Review, Approve, Edit |
| 17 | **Voice Note Transcribed** | AI transcription complete | Duration, accuracy %, word count, confidence, note preview | Review, Approve, Edit |

#### System/Compliance (3)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 18 | **Unauthorized Access Attempt** | Failed/suspicious access to patient records | User/IP, accessed patient, action blocked, date/time | Review Logs, Take Action |
| 19 | **Facility Storage Warning** | Storage ≥ 80% | Used/total storage, days until full, growth rate | Cleanup, Request Upgrade |
| 20 | **Facility Update Required** | System requires facility info update | Field names, deadline | Update Facility Info |

#### Scheduled Reports (3)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 21 | **Weekly Team Performance Report** | Weekly report generated (Mon 8am) | Top performer, avg time, satisfaction, completion rate | View Full Report, Share |
| 22 | **Monthly Facility Analytics** | Monthly report generated (1st of month) | Total referrals, avg time, admission rate, trends | View Full Report, Export |
| 23 | **Referral Trend Report** | Weekly trend analysis | Trend direction, top conditions, busy hours, patterns | View Trends, Export Data |

---

### C. CLINICIAN NOTIFICATIONS (15 types)

Patient care focused + referral actions:

#### Referral Management (5) - **MOST CRITICAL**
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 1 | **Incoming Referral** | Patient referred to clinician | Patient name, urgency, from clinic, condition summary, MRN | Accept/Reject, View Full |
| 2 | **Referral Accepted** | Your referral was accepted | Patient name, receiving facility, accepting physician, ETA | Prepare Patient, Schedule |
| 3 | **Referral Rejected** | Your referral was rejected | Patient name, receiving facility, rejection reason, next steps | Contact Facility, Retry |
| 4 | **Referral Status Update** | Referral changed status (in transit, received, completed) | Patient name, new status, receiving facility, timestamp | View Details, Update Records |
| 5 | **Referral Needs Action** | Missing document, signature, etc | Patient name, action needed, deadline | Take Action, View Details |

#### Patient Care (4)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 6 | **Patient Admitted** | Patient from your referral admitted | Patient name, admit facility, time, ward/bed assignment | Contact Facility, Confirm |
| 7 | **Test Results Available** | Lab/imaging for your patient ready | Patient name, test type, results (normal/abnormal), link | Review, Action Needed |
| 8 | **Patient Follow-up Reminder** | Patient needs follow-up appointment | Patient name, days since admission, recommended actions | Schedule Follow-up, Contact |
| 9 | **New Patient Documents** | Documents added to your patients | Patient name, document type, uploader | Review, Analyze with AI |

#### AI Processing (3)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 10 | **Document Analysis Complete** | Your document was analyzed by AI | Document name, key findings, confidence %, review needed | Review Analysis, Approve |
| 11 | **Voice Note Transcribed** | Your voice note AI transcription ready | Duration, accuracy %, word count, note preview | Review, Approve, Edit |
| 12 | **AI Suggested Action** | AI found something requiring attention | Patient name, finding, AI confidence, recommended action | View Details, Take Action |

#### Facility Communication (2)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 13 | **Clinical Announcement** | Facility posted announcement | Title, announcement text, from facility admin | Read Full, Acknowledge |
| 14 | **Clinical Guideline Update** | New clinical guideline published | Guideline name, affected cases, approval status | Read Guideline, Update Protocols |

#### Performance/Training (2)
| # | Event | Trigger | Details | Actions |
|---|-------|---------|---------|---------|
| 15 | **Weekly Stats Snapshot** | Weekly performance summary | Referrals created, avg time, ratings, pending actions | View Full Stats, Trends |
| 16 | **Training Requirement** | Training/certification due soon | Training name, due date, hours required | Start Training, Renew License |

---

## PART 5: HOW WEBSOCKET NOTIFICATIONS ARE TRIGGERED

### Example: When Super Admin Creates a Facility

```python
# 1. Super Admin calls POST /facilities
@router.post("/facilities")
def create_facility(facility_data, current_user, db):
    # Create facility
    facility = Facility(name=facility_data.name, ...)
    db.add(facility)
    db.commit()
    
    # 2. Trigger notification
    notification_service = get_notification_service(db)
    notification_service.create_facility_creation_notification(facility, current_user)
    
    return facility

# 3. In notification_service.py
def create_facility_creation_notification(self, facility, created_by):
    notification = self.create_notification(
        notification_type="info",
        title="✅ NEW FACILITY CREATED",
        message=f"Facility '{facility.name}' has been created",
        details={
            "facility_id": facility.id,
            "facility_name": facility.name,
            "facility_type": facility.facility_type,
            "location": facility.location,
            "created_by": created_by.first_name,
            "timestamp": datetime.now().isoformat(),
        },
        actions=["View Facility", "Configure"],
        roles=["super_admin"],  # Only super admin gets this
        backend_source="facilities"
    )
    return notification

# 4. create_notification() automatically:
# - Saves to database
# - Calls broadcaster.broadcast_notification()
# - Broadcaster sends via WebSocket to all connected super_admins
```

### Example: When Referral Status Changes

```python
# 1. Clinician accepts referral via PATCH /referrals/{id}/accept
@router.patch("/referrals/{referral_id}/accept")
def accept_referral(referral_id, current_user, db):
    referral = db.query(Referral).filter_by(id=referral_id).first()
    
    # Update status
    referral.status = ReferralStatus.ACCEPTED
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.now()
    db.commit()
    
    # 2. Trigger notifications
    notification_service = get_notification_service(db)
    
    # Notify the sending clinic (who referred patient)
    notification_service.create_referral_accepted_notification(
        referral,
        notify_facility_id=referral.from_facility_id
    )
    
    # Notify the clinician who created referral
    notification_service.create_referral_status_notification(referral)
    
    return referral

# 3. Broadcaster routes:
# - Gets referral.from_facility_id
# - Finds all connected users in that facility with role in [facility_admin, clinician]
# - Sends WebSocket message to each
# - If users offline, message stored in DB for later delivery
```

---

## PART 6: WEBSOCKET CONNECTION & MESSAGE FORMAT

### Connection

```javascript
// Frontend
const token = localStorage.getItem('access_token');
const ws = new WebSocket(
  `wss://backend.mediflow.com/api/v1/websocket/notifications?token=${token}`
);

ws.onopen = () => console.log("Connected to notifications");
ws.onclose = () => console.log("Disconnected, will reconnect in 5s");
ws.onerror = (err) => console.error("WebSocket error:", err);
```

### Message Format Received

```json
{
  "id": 123,
  "type": "critical|warning|info",
  "title": "🚨 EMERGENCY REFERRAL",
  "message": "Cardiac patient requires immediate transfer",
  "details": {
    "patient_id": "P-456",
    "urgency": "life-threatening",
    "referral_id": "R-789",
    "time_sensitive": "30 minutes",
    "referring_facility": "City Hospital"
  },
  "actions": ["📋 Accept Referral", "📞 Contact Referring MD"],
  "roles": ["facility_admin", "clinician"],
  "backend_source": "referrals",
  "timestamp": "2026-05-25T14:30:00Z",
  "expires_at": "2026-05-25T15:30:00Z"
}
```

### WebSocket Lifecycle

```
1. Connect → WebSocket endpoint with JWT
2. Authenticate → Backend verifies JWT
3. Register → Connection stored with user_id, role, facility_id
4. Send Pending → All undelivered notifications sent
5. Listen → Keep connection open, receive new notifications
6. Handle Message → Process notification on frontend
7. Mark Read → Frontend calls PUT /notifications/{id}/read
8. Disconnect → Connection removed from manager
9. Offline → Pending notifications saved in DB
10. Reconnect → Pending notifications sent again
```

---

## PART 7: IMPLEMENTATION RECOMMENDATIONS

### Phase 1: Fix Critical Issues (Week 1)
1. Replace error dicts with HTTPException in analytics endpoints
2. Add facility validation with proper error codes
3. Fix patient count filtering
4. Add try/except blocks

### Phase 2: Add Missing Notifications (Week 2-3)
1. Facility management events
2. Clinician lifecycle events
3. Additional referral status triggers
4. Patient event triggers

### Phase 3: Optimize Performance (Week 3-4)
1. Fix N+1 query problems
2. Use database aggregation instead of Python loops
3. Add connection pooling optimization
4. Implement notification batching

### Phase 4: Frontend Integration (Week 4-5)
1. Implement comprehensive WebSocket handler
2. Add notification center UI
3. Add sound/toast alerts
4. Add persistent notification storage
5. Add unread notification badge

---

## NEXT STEPS

1. **Check your frontend code** - How is it handling the 200 OK with error responses?
2. **Decide notification scope** - Are all 50+ notifications needed or a subset?
3. **Database schema** - Verify notification models support all fields needed
4. **Frontend WebSocket handler** - Need component to receive and display notifications
5. **Testing** - WebSocket connection drops, offline message queuing, re-connection

