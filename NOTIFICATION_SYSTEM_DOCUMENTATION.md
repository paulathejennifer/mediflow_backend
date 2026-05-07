# 🔔 MediFlow Notification System Documentation

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Role-Based Notification Strategy](#role-based-notification-strategy)
3. [Notification Categories](#notification-categories)
4. [Backend Implementation Requirements](#backend-implementation-requirements)
5. [Action Button Implementations](#action-button-implementations)
6. [Frontend Implementation](#frontend-implementation)
7. [WebSocket Architecture](#websocket-architecture)
8. [Database Schema](#database-schema)
9. [API Endpoints](#api-endpoints)
10. [Testing Strategy](#testing-strategy)

---

## 🎯 System Overview

MediFlow's notification system provides real-time, role-appropriate alerts for healthcare professionals. The system leverages existing backend capabilities while providing actionable insights for different user roles.

### 🏗️ Core Principles
- **Role-Based Filtering**: Different notifications for different user roles
- **Real-Time Delivery**: Instant notification via WebSocket
- **Actionable Notifications**: Each notification has specific actions
- **Clinical Focus**: Prioritize patient safety and care quality
- **HIPAA Compliance**: Secure handling of sensitive healthcare data

---

## 👥 Role-Based Notification Strategy

### 🏥 Super Admin
**Scope**: System-wide monitoring and management
- **Critical**: System outages, security breaches, data corruption
- **Warning**: Performance degradation, capacity issues, unusual activity
- **Info**: Weekly reports, new facilities, system updates

### 🏥 Facility Admin (Clinician + Management)
**Scope**: Facility management + clinical practice
- **Shared Clinical**: Same notifications as clinicians
- **Management Only**: Staff coverage, storage, team performance

### 👨‍⚕️ Clinician
**Scope**: Clinical practice only
- **Shared Clinical**: Patient emergencies, referrals, AI processing
- **No Management**: No facility management notifications

---

## 📊 Notification Categories

### 🔴 Critical Notifications (Immediate Action Required)

#### Shared by Facility Admin & Clinician
```javascript
// 1. Emergency Referral
{
  "id": "shared_crit_001",
  "type": "critical",
  "title": "🚨 EMERGENCY REFERRAL",
  "message": "Cardiac patient requires immediate transfer",
  "details": {
    "patient_id": "P-12345",
    "urgency": "life-threatening",
    "referral_id": "R-67890",
    "time_sensitive": "30 minutes",
    "referring_facility": "City General Hospital"
  },
  "actions": ["📋 Accept Referral", "📞 Contact Referring MD"],
  "timestamp": "2024-01-15T16:20:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "referrals",
  "trigger_condition": "referral.priority === 'emergency'"
}

// 2. HIPAA Violation
{
  "id": "shared_crit_002",
  "type": "critical",
  "title": "🔒 HIPAA COMPLIANCE VIOLATION",
  "message": "Unauthorized patient record access detected",
  "details": {
    "user_id": 456,
    "accessed_records": 89,
    "authorization_level": "insufficient",
    "audit_log_id": "A-123456",
    "facility": "St. Mary's Hospital"
  },
  "actions": ["🚨 Suspend User", "📋 File Compliance Report"],
  "timestamp": "2024-01-15T15:45:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "audit_logs",
  "trigger_condition": "audit.action === 'access_denied' && audit.details.unauthorized_access === true"
}

// 3. Patient Emergency
{
  "id": "shared_crit_003",
  "type": "critical",
  "title": "🚨 PATIENT EMERGENCY",
  "message": "John Doe's vital signs critical",
  "details": {
    "patient_id": "P-67890",
    "vitals": {
      "heart_rate": "45 bpm",
      "blood_pressure": "80/40",
      "oxygen_sat": "78%"
    },
    "location": "Room 204",
    "last_check": "5 minutes ago"
  },
  "actions": ["🚑 Call Code Blue", "📋 Update Patient Status"],
  "timestamp": "2024-01-15T18:30:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "patients",
  "trigger_condition": "patient.vitals.critical === true"
}

// 4. Medication Error
{
  "id": "shared_crit_004",
  "type": "critical",
  "title": "🚨 MEDICATION ERROR",
  "message": "Wrong medication administered",
  "details": {
    "patient_id": "P-54321",
    "wrong_medication": "Epinephrine",
    "correct_medication": "Atropine",
    "administered_by": "Nurse Sarah Smith",
    "time_administered": "15 minutes ago"
  },
  "actions": ["📞 Contact Pharmacy", "📋 File Incident Report"],
  "timestamp": "2024-01-15T19:15:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "medications",
  "trigger_condition": "medication.error === true"
}

// 5. Data Corruption
{
  "id": "shared_crit_005",
  "type": "critical",
  "title": "💾 PATIENT DATA CORRUPTION",
  "message": "Patient records corrupted",
  "details": {
    "affected_patients": 12,
    "corrupted_records": 45,
    "data_type": "referral_documents",
    "backup_available": true,
    "last_backup": "2024-01-14T02:00:00Z"
  },
  "actions": ["🔄 Restore Records", "📞 Contact IT Support"],
  "timestamp": "2024-01-15T20:00:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "database",
  "trigger_condition": "data_integrity_check.failed === true"
}
```

#### Super Admin Only
```javascript
// 6. AI Services Down
{
  "id": "sa_crit_001",
  "type": "critical",
  "title": "🚨 AI SERVICES OFFLINE",
  "message": "Groq Llama 3.1 service unreachable",
  "details": {
    "service": "text_summarization",
    "endpoint": "/api/v1/ai/health",
    "error_count": 127,
    "last_success": "2024-01-15T14:20:00Z"
  },
  "actions": ["🔧 Restart Services", "📊 Check System Logs"],
  "timestamp": "2024-01-15T14:45:00Z",
  "roles": ["super_admin"],
  "backend_source": "ai_services",
  "trigger_condition": "ai_service.health === 'down'"
}

// 7. Database Connection Failed
{
  "id": "sa_crit_002", 
  "type": "critical",
  "title": "🚨 DATABASE CONNECTION FAILED",
  "message": "PostgreSQL connection timeout",
  "details": {
    "database": "mediflow_prod",
    "connection_pool": "exhausted",
    "active_connections": 100,
    "max_connections": 100
  },
  "actions": ["🔄 Restart Database", "📊 Monitor Connections"],
  "timestamp": "2024-01-15T15:30:00Z",
  "roles": ["super_admin"],
  "backend_source": "database",
  "trigger_condition": "database.connection.status === 'failed'"
}

// 8. File Storage Full
{
  "id": "sa_crit_003",
  "type": "critical",
  "title": "🚨 STORAGE CAPACITY EXCEEDED",
  "message": "Upload directory at 100% capacity",
  "details": {
    "upload_dir": "/uploads",
    "used_space": "10TB",
    "total_space": "10TB",
    "failed_uploads": 45
  },
  "actions": ["💾 Cleanup Storage", "📈 Upgrade Storage"],
  "timestamp": "2024-01-15T16:15:00Z",
  "roles": ["super_admin"],
  "backend_source": "file_system",
  "trigger_condition": "storage.usage >= 100%"
}
```

### 🟡 Warning Notifications (Attention Needed Soon)

#### Shared by Facility Admin & Clinician
```javascript
// 1. Referral Delays
{
  "id": "shared_warn_001",
  "type": "warning",
  "title": "⚠️ REFERRAL PROCESSING DELAYS",
  "message": "Average processing time exceeded SLA",
  "details": {
    "sla_target": "2 hours",
    "current_avg": "3.8 hours",
    "backlog_count": 45,
    "affected_departments": ["Cardiology", "Neurology"]
  },
  "actions": ["📋 Review Backlog", "👥 Reassign Staff"],
  "timestamp": "2024-01-15T14:20:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "referrals",
  "trigger_condition": "referral.processing_time > sla_target * 1.5"
}

// 2. AI Performance Drop
{
  "id": "shared_warn_002",
  "type": "warning",
  "title": "⚠️ AI PERFORMANCE DEGRADING",
  "message": "AI accuracy below threshold",
  "details": {
    "accuracy": "85%",
    "required_minimum": "90%",
    "affected_services": ["whisper", "ocr"],
    "impact": "12 clinicians"
  },
  "actions": ["🔧 Restart AI Services", "📊 View Analytics"],
  "timestamp": "2024-01-15T13:15:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "ai_services",
  "trigger_condition": "ai.accuracy < required_minimum"
}

// 3. AI Accuracy Drop (Individual)
{
  "id": "shared_warn_003",
  "type": "warning",
  "title": "⚠️ VOICE TRANSCRIPTION QUALITY",
  "message": "Your transcriptions accuracy below threshold",
  "details": {
    "your_accuracy": "82%",
    "required_minimum": "90%",
    "affected_recordings": 8,
    "common_errors": ["medical_terms", "drug_names"],
    "facility_avg": "94%"
  },
  "actions": ["🎤 Re-record Notes", "📝 Manual Review"],
  "timestamp": "2024-01-15T15:45:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "voice_notes",
  "trigger_condition": "voice_note.accuracy < required_minimum"
}

// 4. Pending Referrals
{
  "id": "shared_warn_004",
  "type": "warning",
  "title": "⚠️ PENDING REFERRALS OVERDUE",
  "message": "5 referrals require your attention",
  "details": {
    "pending_count": 5,
    "overdue_count": 3,
    "oldest_pending": "48 hours ago",
    "urgent_cases": 2,
    "department": "Cardiology"
  },
  "actions": ["📋 Review Referrals", "📞 Contact Patients"],
  "timestamp": "2024-01-15T16:30:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "referrals",
  "trigger_condition": "referral.status === 'pending' && referral.age > 24h"
}

// 5. Patient Follow-up
{
  "id": "shared_warn_005",
  "type": "warning",
  "title": "⚠️ PATIENT FOLLOW-UP NEEDED",
  "message": "Critical lab results require attention",
  "details": {
    "patient_id": "P-98765",
    "test_type": "Blood cultures",
    "result": "Positive for MRSA",
    "treatment_required": "Antibiotic therapy",
    "time_sensitive": "48 hours"
  },
  "actions": ["📞 Contact Patient", "📋 Update Treatment Plan"],
  "timestamp": "2024-01-15T17:15:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "patients",
  "trigger_condition": "patient.lab_results.critical === true && !patient.follow_up_completed"
}

// 6. Document Processing Failed
{
  "id": "shared_warn_006",
  "type": "warning",
  "title": "⚠️ DOCUMENT PROCESSING FAILED",
  "message": "OCR failed on uploaded documents",
  "details": {
    "failed_documents": 3,
    "document_types": ["lab_report", "discharge_summary"],
    "error_type": "image_quality",
    "reupload_needed": true
  },
  "actions": ["📄 Re-upload Documents", "📷 Check Image Quality"],
  "timestamp": "2024-01-15T18:00:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "documents",
  "trigger_condition": "document.processing_status === 'failed'"
}
```

#### Facility Admin Only
```javascript
// 7. Staff Coverage Warning
{
  "id": "fa_only_warn_001",
  "type": "warning",
  "title": "⚠️ STAFF COVERAGE WARNING",
  "message": "Emergency room coverage below minimum",
  "details": {
    "required_staff": 8,
    "available_staff": 4,
    "shift_coverage": "50%",
    "peak_hours": "6PM - 2AM",
    "risk_level": "high"
  },
  "actions": ["👥 Call Backup Staff", "📅 Adjust Schedule"],
  "timestamp": "2024-01-15T17:30:00Z",
  "roles": ["facility_admin"],
  "backend_source": "staffing",
  "trigger_condition": "staffing.coverage < minimum_required"
}

// 8. Storage Warning
{
  "id": "fa_only_warn_002",
  "type": "warning",
  "title": "⚠️ FACILITY STORAGE WARNING",
  "message": "Document storage at 85% capacity",
  "details": {
    "used_storage": "4.2TB",
    "total_storage": "5TB",
    "days_until_full": 7,
    "growth_rate": "120GB/day"
  },
  "actions": ["💾 Cleanup Storage", "📈 Request Upgrade"],
  "timestamp": "2024-01-15T12:45:00Z",
  "roles": ["facility_admin"],
  "backend_source": "file_system",
  "trigger_condition": "facility_storage.usage >= 85%"
}
```

#### Super Admin Only
```javascript
// 9. High Error Rate
{
  "id": "sa_warn_001",
  "type": "warning",
  "title": "⚠️ HIGH ERROR RATE DETECTED",
  "message": "API error rate increased to 15%",
  "details": {
    "normal_rate": "2%",
    "current_rate": "15%",
    "affected_endpoints": ["/ai/test-summary", "/documents/upload"],
    "time_period": "last_hour"
  },
  "actions": ["📊 View Analytics", "🔧 Investigate Endpoints"],
  "timestamp": "2024-01-15T11:20:00Z",
  "roles": ["super_admin"],
  "backend_source": "api_monitoring",
  "trigger_condition": "api.error_rate > 10%"
}

// 10. Slow Response Times
{
  "id": "sa_warn_002",
  "type": "warning", 
  "title": "⚠️ SLOW API RESPONSE TIMES",
  "message": "Average response time exceeded 5 seconds",
  "details": {
    "avg_response_time": "5.2s",
    "sla_target": "2s",
    "slowest_endpoint": "/ai/test-transcription",
    "affected_users": 234
  },
  "actions": ["📊 Performance Review", "🔧 Optimize Queries"],
  "timestamp": "2024-01-15T12:45:00Z",
  "roles": ["super_admin"],
  "backend_source": "api_monitoring",
  "trigger_condition": "api.response_time > sla_target * 2.5"
}
```

### 🔵 Info Notifications (Informational Updates)

#### Shared by Facility Admin & Clinician
```javascript
// 1. Referral Status Update
{
  "id": "shared_info_001",
  "type": "info",
  "title": "📋 REFERRAL STATUS UPDATE",
  "message": "Your cardiology referral was accepted",
  "details": {
    "patient_name": "John Doe",
    "referral_id": "R-12345",
    "accepting_facility": "St. Mary's Hospital",
    "accepting_physician": "Dr. Robert Chen",
    "estimated_arrival": "2024-01-15T16:00:00Z"
  },
  "actions": ["📋 View Details", "📞 Prepare Patient"],
  "timestamp": "2024-01-15T13:45:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "referrals",
  "trigger_condition": "referral.status === 'accepted'"
}

// 2. AI Processing Complete
{
  "id": "shared_info_002",
  "type": "info",
  "title": "🤖 VOICE NOTE TRANSCRIBED",
  "message": "Patient assessment transcription ready",
  "details": {
    "recording_duration": "12 minutes",
    "accuracy": "96.8%",
    "word_count": 1,247,
    "processing_time": "1.1 minutes"
  },
  "actions": ["📝 Review Transcript", "✅ Approve Note"],
  "timestamp": "2024-01-15T14:30:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "voice_notes",
  "trigger_condition": "voice_note.status === 'transcribed'"
}

// 3. Document Extracted
{
  "id": "shared_info_003",
  "type": "info",
  "title": "📄 DOCUMENT TEXT EXTRACTED",
  "message": "Lab report OCR processing complete",
  "details": {
    "document_type": "lab_report",
    "pages_processed": 5,
    "text_extracted": "2,345 words",
    "confidence_score": "94.2%"
  },
  "actions": ["📋 Review Extracted Text", "✅ Approve Document"],
  "timestamp": "2024-01-15T15:15:00Z",
  "roles": ["facility_admin", "clinician"],
  "backend_source": "documents",
  "trigger_condition": "document.status === 'extracted'"
}
```

#### Facility Admin Only
```javascript
// 4. Team Performance
{
  "id": "fa_only_info_001",
  "type": "info",
  "title": "👥 WEEKLY TEAM PERFORMANCE",
  "message": "Clinician performance summary ready",
  "details": {
    "top_performer": "Dr. Mike Wilson",
    "avg_referral_time": "1.2 hours",
    "patient_satisfaction": "4.7/5.0",
    "completion_rate": "96%"
  },
  "actions": ["🎉 Recognize Team", "📊 View Details"],
  "timestamp": "2024-01-15T09:00:00Z",
  "roles": ["facility_admin"],
  "backend_source": "analytics",
  "trigger_condition": "weekly_report_generated === true"
}

// 5. New Staff
{
  "id": "fa_only_info_002",
  "type": "info",
  "title": "👥 NEW CLINICIAN JOINED",
  "message": "Dr. Emily Chen added to cardiology",
  "details": {
    "clinician_name": "Dr. Emily Chen",
    "department": "Cardiology",
    "start_date": "2024-01-15",
    "experience": "5 years"
  },
  "actions": ["👋 Welcome Staff", "📋 Update Schedule"],
  "timestamp": "2024-01-15T10:30:00Z",
  "roles": ["facility_admin"],
  "backend_source": "users",
  "trigger_condition": "user.role === 'clinician' && user.created === today"
}

// 6. Training Available
{
  "id": "fa_only_info_003",
  "type": "info",
  "title": "📚 TRAINING OPPORTUNITY",
  "message": "AI voice note techniques workshop",
  "details": {
    "course_title": "Optimizing Medical Dictation",
    "duration": "2 hours",
    "credits": "2 CME",
    "start_date": "2024-01-20T14:00:00Z"
  },
  "actions": ["📚 Enroll Staff", "📅 Add to Calendar"],
  "timestamp": "2024-01-15T11:15:00Z",
  "roles": ["facility_admin"],
  "backend_source": "training",
  "trigger_condition": "training.available === true"
}
```

#### Super Admin Only
```javascript
// 7. Weekly Report
{
  "id": "sa_info_001",
  "type": "info",
  "title": "📊 WEEKLY SYSTEM REPORT",
  "message": "System performance summary ready",
  "details": {
    "total_users": 1842,
    "active_facilities": 127,
    "referrals_processed": 12456,
    "ai_accuracy": "98.7%",
    "uptime": "99.8%"
  },
  "actions": ["📈 View Report", "📥 Download CSV"],
  "timestamp": "2024-01-15T09:00:00Z",
  "roles": ["super_admin"],
  "backend_source": "analytics",
  "trigger_condition": "weekly_report_generated === true"
}

// 8. New Facility
{
  "id": "sa_info_002",
  "type": "info",
  "title": "🏥 NEW FACILITY JOINED",
  "message": "Riverside Medical Center onboarded",
  "details": {
    "facility_name": "Riverside Medical Center",
    "location": "California",
    "clinicians_added": 24,
    "facility_level": "level_4"
  },
  "actions": ["👥 View Facility", "📋 Welcome Team"],
  "timestamp": "2024-01-15T10:30:00Z",
  "roles": ["super_admin"],
  "backend_source": "facilities",
  "trigger_condition": "facility.status === 'active' && facility.created === today"
}

// 9. System Update
{
  "id": "sa_info_003",
  "type": "info",
  "title": "🔄 SYSTEM UPDATE COMPLETED",
  "message": "Backend services updated successfully",
  "details": {
    "version": "v2.1.0",
    "updated_services": ["auth", "ai", "documents"],
    "downtime": "2 minutes",
    "new_features": ["enhanced_ocr", "voice_quality"]
  },
  "actions": ["📋 View Changelog", "✅ Confirm Health"],
  "timestamp": "2024-01-15T08:00:00Z",
  "roles": ["super_admin"],
  "backend_source": "system",
  "trigger_condition": "system.update_completed === true"
}
```

---

## 🔧 Backend Implementation Requirements

### 📊 Why Backend Implementation is Necessary

#### 1. **Real-Time Monitoring**
```python
# Need to monitor system health and trigger notifications
class NotificationMonitor:
    def __init__(self):
        self.ai_service_health = AIServiceHealth()
        self.database_monitor = DatabaseMonitor()
        self.file_system_monitor = FileSystemMonitor()
    
    async def start_monitoring(self):
        # Monitor AI services every 30 seconds
        asyncio.create_task(self.monitor_ai_services())
        
        # Monitor database every minute
        asyncio.create_task(self.monitor_database())
        
        # Monitor file storage every 5 minutes
        asyncio.create_task(self.monitor_storage())
```

#### 2. **Event-Driven Notifications**
```python
# Need to capture events from existing system
class NotificationEventHandler:
    def __init__(self):
        self.websocket_manager = WebSocketManager()
        self.notification_service = NotificationService()
    
    async def handle_referral_created(self, referral_data):
        if referral_data.priority === 'emergency':
            await self.send_critical_notification(referral_data)
    
    async def handle_ai_service_down(self, service_name):
        await self.send_system_alert(service_name)
```

#### 3. **WebSocket Real-Time Delivery**
```python
# Need WebSocket for real-time notifications
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str):
        await websocket.accept()
        self.active_connections[user_id] = {
            'websocket': websocket,
            'role': user_role,
            'connected_at': datetime.utcnow()
        }
    
    async def send_notification(self, notification: dict, target_roles: list):
        for user_id, conn in self.active_connections.items():
            if conn['role'] in target_roles:
                await conn['websocket'].send_json(notification)
```

### 🗄️ Database Schema Additions

#### New Tables Needed
```sql
-- Notifications table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    notification_type VARCHAR(20) NOT NULL, -- critical, warning, info
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    actions JSONB,
    roles JSONB NOT NULL,
    backend_source VARCHAR(50) NOT NULL,
    trigger_condition TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Notification delivery tracking
CREATE TABLE notification_delivery (
    id SERIAL PRIMARY KEY,
    notification_id INTEGER REFERENCES notifications(id),
    user_id INTEGER REFERENCES users(id),
    delivery_method VARCHAR(20), -- websocket, email, push
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    action_taken VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System monitoring data
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,2),
    threshold_value DECIMAL(10,2),
    status VARCHAR(20), -- normal, warning, critical
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 🎯 Implementation Strategy

#### Phase 1: Core Infrastructure (Week 1)
1. **Database Schema**: Create notification tables
2. **WebSocket Manager**: Real-time delivery system
3. **Base Notification Service**: Core notification logic
4. **Role-Based Filtering**: User role management

#### Phase 2: Event Integration (Week 2)
1. **Referral Events**: Emergency referral triggers
2. **AI Service Monitoring**: Health check integration
3. **Database Monitoring**: Connection and performance
4. **File System Monitoring**: Storage capacity

#### Phase 3: Action Implementation (Week 3)
1. **Action Handlers**: Implement all action buttons
2. **Email Integration**: Critical notifications via email
3. **SMS Integration**: Emergency notifications
4. **Push Notifications**: Mobile app support

#### Phase 4: Advanced Features (Week 4)
1. **Notification Analytics**: Delivery and engagement tracking
2. **Smart Filtering**: ML-based notification relevance
3. **Batch Processing**: Efficient notification delivery
4. **Compliance Reporting**: HIPAA audit trails

---

## 🎯 Action Button Implementations

### 🚨 Critical Action Implementations

#### 1. "Accept Referral" Action
```python
@router.post("/notifications/{notification_id}/actions/accept-referral")
async def accept_referral_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get notification details
    notification = get_notification_by_id(notification_id, db)
    referral_id = notification.details['referral_id']
    
    # Update referral status
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    referral.status = ReferralStatus.ACCEPTED
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.utcnow()
    
    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="accept_referral",
        entity_type="referral",
        entity_id=referral_id,
        details={"notification_id": notification_id}
    )
    
    # Send confirmation notification
    await send_notification_to_referring_facility(referral)
    
    return {"message": "Referral accepted successfully", "referral_id": referral_id}
```

#### 2. "Call Code Blue" Action
```python
@router.post("/notifications/{notification_id}/actions/call-code-blue")
async def call_code_blue_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get patient details
    notification = get_notification_by_id(notification_id, db)
    patient_id = notification.details['patient_id']
    
    # Create emergency response record
    emergency = EmergencyResponse(
        patient_id=patient_id,
        initiated_by=current_user.id,
        emergency_type="code_blue",
        status="active",
        initiated_at=datetime.utcnow()
    )
    db.add(emergency)
    
    # Notify all clinical staff at facility
    await notify_clinical_staff(
        facility_id=current_user.facility_id,
        message=f"CODE BLUE - Room {notification.details['location']}",
        priority="critical"
    )
    
    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="initiate_code_blue",
        entity_type="patient",
        entity_id=patient_id,
        details={"location": notification.details['location']}
    )
    
    return {"message": "Code Blue initiated", "patient_id": patient_id}
```

#### 3. "Suspend User" Action
```python
@router.post("/notifications/{notification_id}/actions/suspend-user")
async def suspend_user_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get violation details
    notification = get_notification_by_id(notification_id, db)
    violating_user_id = notification.details['user_id']
    
    # Suspend user account
    violating_user = db.query(User).filter(User.id == violating_user_id).first()
    violating_user.is_active = False
    violating_user.suspended_at = datetime.utcnow()
    violating_user.suspended_by = current_user.id
    
    # Create compliance report
    compliance_report = ComplianceReport(
        user_id=violating_user_id,
        reported_by=current_user.id,
        violation_type="unauthorized_access",
        details=notification.details,
        status="investigating"
    )
    db.add(compliance_report)
    
    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="suspend_user",
        entity_type="user",
        entity_id=violating_user_id,
        details={"reason": "hipaa_violation", "notification_id": notification_id}
    )
    
    # Notify security team
    await notify_security_team(violating_user_id, notification.details)
    
    return {"message": "User suspended successfully", "user_id": violating_user_id}
```

### ⚠️ Warning Action Implementations

#### 4. "Review Backlog" Action
```python
@router.get("/notifications/{notification_id}/actions/review-backlog")
async def review_backlog_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get overdue referrals
    overdue_referrals = db.query(Referral).filter(
        and_(
            Referral.status == ReferralStatus.PENDING,
            Referral.created_at < datetime.utcnow() - timedelta(hours=24),
            Referral.assigned_to == current_user.id
        )
    ).all()
    
    # Return detailed backlog information
    return {
        "backlog_count": len(overdue_referrals),
        "referrals": [
            {
                "id": r.id,
                "patient_name": r.patient.first_name + " " + r.patient.last_name,
                "priority": r.priority,
                "created_at": r.created_at,
                "age_hours": (datetime.utcnow() - r.created_at).total_seconds() / 3600
            }
            for r in overdue_referrals
        ]
    }
```

#### 5. "Restart AI Services" Action
```python
@router.post("/notifications/{notification_id}/actions/restart-ai-services")
async def restart_ai_services_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only super admin can restart services
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Restart AI services
    ai_services = ["groq", "whisper", "tesseract"]
    restart_results = {}
    
    for service in ai_services:
        try:
            # Implement service restart logic
            result = restart_service(service)
            restart_results[service] = "success"
        except Exception as e:
            restart_results[service] = f"failed: {str(e)}"
    
    # Log action
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="restart_ai_services",
        entity_type="system",
        details={"services": restart_results, "notification_id": notification_id}
    )
    
    return {
        "message": "AI services restart initiated",
        "results": restart_results
    }
```

### 🔵 Info Action Implementations

#### 6. "View Details" Action
```python
@router.get("/notifications/{notification_id}/actions/view-details")
async def view_details_action(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get full notification details
    notification = get_notification_by_id(notification_id, db)
    
    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    
    # Return detailed information based on source
    if notification.backend_source == "referrals":
        referral = db.query(Referral).filter(
            Referral.id == notification.details['referral_id']
        ).first()
        return {"referral_details": referral.to_dict()}
    
    elif notification.backend_source == "voice_notes":
        voice_note = db.query(VoiceNote).filter(
            VoiceNote.id == notification.details['voice_note_id']
        ).first()
        return {"voice_note_details": voice_note.to_dict()}
    
    return {"details": notification.details}
```

#### 7. "Download Report" Action
```python
@router.get("/notifications/{notification_id}/actions/download-report")
async def download_report_action(
    notification_id: int,
    format: str = "csv",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get notification details
    notification = get_notification_by_id(notification_id, db)
    
    # Generate report based on type
    if notification.backend_source == "analytics":
        if format == "csv":
            csv_data = generate_csv_report(notification.details)
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=report.csv"}
            )
        elif format == "pdf":
            pdf_data = generate_pdf_report(notification.details)
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=report.pdf"}
            )
    
    return {"message": "Report generation failed"}
```

---

## 🎨 Frontend Implementation

### 📱 Notification Center Component
```javascript
// React component for notification center
const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [filters, setFilters] = useState({ type: 'all', role: 'all' });
  const [ws, setWs] = useState(null);
  
  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket(`wss://api.mediflow.com/notifications?token=${getToken()}`);
    
    websocket.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications(prev => [notification, ...prev]);
      
      // Show toast for critical/warning
      if (['critical', 'warning'].includes(notification.type)) {
        showToast(notification);
      }
    };
    
    setWs(websocket);
    
    return () => websocket.close();
  }, []);
  
  const handleAction = async (notificationId, action) => {
    try {
      const response = await fetch(`/api/v1/notifications/${notificationId}/actions/${action}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      
      const result = await response.json();
      
      // Update notification state
      setNotifications(prev => 
        prev.map(n => n.id === notificationId 
          ? { ...n, action_taken: action, action_result: result }
          : n
        )
      );
      
      return result;
    } catch (error) {
      console.error('Action failed:', error);
    }
  };
  
  const filteredNotifications = notifications.filter(notification => {
    const typeMatch = filters.type === 'all' || notification.type === filters.type;
    const roleMatch = filters.role === 'all' || 
      notification.roles.includes(getCurrentUser().role);
    return typeMatch && roleMatch;
  });
  
  return (
    <div className="notification-center">
      <div className="notification-filters">
        <select value={filters.type} onChange={(e) => setFilters({...filters, type: e.target.value})}>
          <option value="all">All Types</option>
          <option value="critical">🔴 Critical</option>
          <option value="warning">🟡 Warning</option>
          <option value="info">🔵 Info</option>
        </select>
      </div>
      
      <div className="notification-list">
        {filteredNotifications.map(notification => (
          <NotificationCard 
            key={notification.id}
            notification={notification}
            onAction={handleAction}
          />
        ))}
      </div>
    </div>
  );
};
```

### 🎯 Notification Card Component
```javascript
const NotificationCard = ({ notification, onAction }) => {
  const badgeClass = `badge-${notification.type}`;
  const isExpired = new Date(notification.expires_at) < new Date();
  
  return (
    <div className={`notification-card ${badgeClass} ${isExpired ? 'expired' : ''}`}>
      <div className="notification-header">
        <span className={`badge ${badgeClass}`}>
          {notification.type === 'critical' ? '🔴' : 
           notification.type === 'warning' ? '🟡' : '🔵'}
        </span>
        <h3>{notification.title}</h3>
        <span className="timestamp">
          {formatRelativeTime(notification.timestamp)}
        </span>
      </div>
      
      <p className="notification-message">{notification.message}</p>
      
      {notification.details && (
        <div className="notification-details">
          <DetailsAccordion details={notification.details} />
        </div>
      )}
      
      <div className="notification-actions">
        {notification.actions.map(action => (
          <ActionButton
            key={action}
            action={action}
            notificationId={notification.id}
            onAction={onAction}
          />
        ))}
      </div>
    </div>
  );
};
```

### 🎯 Action Button Component
```javascript
const ActionButton = ({ action, notificationId, onAction }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  const handleClick = async () => {
    setIsLoading(true);
    try {
      const actionResult = await onAction(notificationId, action);
      setResult(actionResult);
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <button 
      className={`action-button ${action.toLowerCase().replace(/\s+/g, '-')}`}
      onClick={handleClick}
      disabled={isLoading}
    >
      {isLoading ? 'Processing...' : action}
    </button>
  );
};
```

---

## 🌐 WebSocket Architecture

### 🔌 WebSocket Connection Manager
```python
# app/websocket/manager.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_roles: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_roles[user_id] = user_role
        
        # Send initial notifications
        await self.send_pending_notifications(user_id)
    
    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].close()
            del self.active_connections[user_id]
            del self.user_roles[user_id]
    
    async def send_to_user(self, user_id: str, notification: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(notification)
    
    async def broadcast_to_role(self, role: str, notification: dict):
        for user_id, user_role in self.user_roles.items():
            if user_role == role:
                await self.send_to_user(user_id, notification)
    
    async def broadcast_to_roles(self, roles: list, notification: dict):
        for user_id, user_role in self.user_roles.items():
            if user_role in roles:
                await self.send_to_user(user_id, notification)
```

### 🎯 WebSocket Endpoint
```python
# app/api/v1/websocket.py
@router.websocket("/notifications")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Verify token and get user
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user:
            await websocket.close(code=4001)
            return
            
    except Exception:
        await websocket.close(code=4001)
        return
    
    # Connect to manager
    await manager.connect(websocket, str(user.id), user.role)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(str(user.id))
```

---

## 📊 Testing Strategy

### 🧪 Unit Tests
```python
# tests/test_notifications.py
class TestNotificationService:
    def test_create_critical_notification(self):
        notification = notification_service.create_notification(
            type="critical",
            title="Test Emergency",
            message="Test message",
            roles=["clinician", "facility_admin"]
        )
        assert notification.type == "critical"
        assert notification.roles == ["clinician", "facility_admin"]
    
    def test_role_based_filtering(self):
        notifications = [
            {"roles": ["super_admin"], "type": "critical"},
            {"roles": ["clinician", "facility_admin"], "type": "warning"},
            {"roles": ["facility_admin"], "type": "info"}
        ]
        
        filtered = notification_service.filter_by_role(notifications, "clinician")
        assert len(filtered) == 1
        assert filtered[0]["type"] == "warning"
```

### 🔄 Integration Tests
```python
# tests/test_notification_actions.py
class TestNotificationActions:
    def test_accept_referral_action(self):
        # Create test referral
        referral = create_test_referral()
        notification = create_test_notification(referral)
        
        # Test action
        result = notification_service.accept_referral(notification.id, test_user.id)
        
        assert result["referral_id"] == referral.id
        assert referral.status == ReferralStatus.ACCEPTED
    
    def test_code_blue_action(self):
        # Create test patient
        patient = create_test_patient()
        notification = create_test_notification(patient)
        
        # Test action
        result = notification_service.call_code_blue(notification.id, test_user.id)
        
        assert result["patient_id"] == patient.id
        assert emergency_response_exists(patient.id)
```

### 🌐 End-to-End Tests
```python
# tests/test_e2e_notifications.py
class TestNotificationE2E:
    def test_emergency_referral_flow(self):
        # 1. Create emergency referral
        referral = create_emergency_referral()
        
        # 2. Connect WebSocket as clinician
        ws_client = connect_websocket("clinician")
        
        # 3. Verify notification received
        notification = ws_client.receive_notification()
        assert notification["type"] == "critical"
        assert notification["title"] == "🚨 EMERGENCY REFERRAL"
        
        # 4. Test accept referral action
        result = ws_client.send_action("accept-referral")
        assert result["referral_id"] == referral.id
        
        # 5. Verify referral status updated
        updated_referral = get_referral(referral.id)
        assert updated_referral.status == "accepted"
```

---

## 🚀 Deployment Considerations

### 🔧 Environment Variables
```env
# Notification System
NOTIFICATION_WS_URL=wss://api.mediflow.com/notifications
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_BATCH_SIZE=100

# Action Handlers
CODE_BLUE_PHONE_NUMBER=+1234567890
SECURITY_TEAM_EMAIL=security@mediflow.com

# Monitoring
NOTIFICATION_METRICS_ENABLED=true
NOTIFICATION_ANALYTICS_ENABLED=true
```

### 📊 Performance Optimization
```python
# Notification caching
@cache.memoize(timeout=300)  # 5 minutes
def get_user_notifications(user_id: int, role: str):
    return notification_service.get_notifications(user_id, role)

# Batch notification processing
async def batch_send_notifications(notifications: list):
    tasks = []
    for notification in notifications:
        tasks.append(send_notification(notification))
    
    await asyncio.gather(*tasks, return_exceptions=True)
```

### 🔒 Security Considerations
```python
# WebSocket authentication
async def authenticate_websocket(token: str):
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        # Check if user is still active
        user = get_user_by_id(user_id)
        if not user or not user.is_active:
            return None
            
        return user
    except Exception:
        return None

# Rate limiting
@limiter.limit("100/minute")
async def send_notification_endpoint(user_id: str, notification: dict):
    return await send_notification(user_id, notification)
```

---

## 📈 Monitoring & Analytics

### 📊 Notification Metrics
```python
class NotificationMetrics:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    def track_notification_sent(self, notification: dict):
        self.metrics_collector.increment_counter(
            "notifications_sent",
            tags={
                "type": notification["type"],
                "role": notification["roles"][0],
                "source": notification["backend_source"]
            }
        )
    
    def track_action_taken(self, notification_id: int, action: str):
        self.metrics_collector.increment_counter(
            "notification_actions_taken",
            tags={"action": action}
        )
    
    def track_delivery_time(self, notification_id: int, delivery_time: float):
        self.metrics_collector.record_histogram(
            "notification_delivery_time",
            delivery_time,
            tags={"notification_id": str(notification_id)}
        )
```

### 📈 Analytics Dashboard
```javascript
// Notification analytics component
const NotificationAnalytics = () => {
  const [metrics, setMetrics] = useState(null);
  
  useEffect(() => {
    fetchNotificationMetrics().then(setMetrics);
  }, []);
  
  return (
    <div className="analytics-dashboard">
      <MetricCard 
        title="Notifications Sent Today"
        value={metrics?.notifications_sent_today}
        change={metrics?.sent_change_percent}
      />
      <MetricCard 
        title="Action Completion Rate"
        value={metrics?.action_completion_rate}
        change={metrics?.completion_change_percent}
      />
      <MetricCard 
        title="Average Response Time"
        value={metrics?.avg_response_time}
        change={metrics?.response_time_change}
      />
    </div>
  );
};
```

---

## 🎯 Conclusion

The MediFlow notification system provides a comprehensive, role-based alert system that leverages existing backend capabilities while adding real-time, actionable notifications. The system is designed to:

1. **Enhance Patient Safety**: Critical alerts for medical emergencies
2. **Improve System Reliability**: Proactive monitoring and alerts
3. **Streamline Workflow**: Actionable notifications with direct actions
4. **Ensure Compliance**: HIPAA-compliant audit trails and logging
5. **Scale Effectively**: WebSocket-based real-time delivery

The implementation uses existing MediFlow infrastructure while adding minimal new components, making it both powerful and maintainable. The system is designed to evolve with the platform and can easily accommodate new notification types and actions as the system grows.

---

*Last Updated: January 2024*
*Version: 1.0.0*
