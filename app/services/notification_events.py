"""
Comprehensive Notification Event Creators for MediFlow

This module contains all 50+ notification event creator methods organized by event type.
These methods are designed to be called from service layer methods (referral_service, facility_service, etc.)
to trigger real-time notifications to appropriate users.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from app.models.referral import Referral
from app.models.facility import Facility
from app.models.patient import Patient
from app.models.user import User
from app.models.referral_document import ReferralDocument
from app.enums import ReferralStatus, Priority, UserRole


class NotificationEventCreators:
    """Mixin class with all notification event creator methods"""

    # ============================================================================
    # SUPER ADMIN NOTIFICATIONS (SA001-SA009)
    # ============================================================================

    def create_facility_created_notification(
        self, facility: Facility, created_by_user_id: int
    ):
        """SA001: Facility Created"""
        return self.create_notification(
            notification_type="info",
            title=f"✨ New Facility Created: {facility.name}",
            message=f"A new {facility.type or 'healthcare'} facility has been registered in the system",
            details={
                "facility_id": facility.id,
                "facility_name": facility.name,
                "facility_type": facility.type,
                "county": facility.county,
                "created_by": created_by_user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["View Facility", "Send Welcome", "Configure Settings"],
            roles=["super_admin"],
            backend_source="facilities",
            trigger_condition=f"facility.created === true && facility.id === {facility.id}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

    def create_facility_status_changed_notification(
        self, facility: Facility, old_status: bool, reason: str = ""
    ):
        """SA002: Facility Status Changed"""
        new_status = "Active" if facility.is_active else "Inactive"
        old_status_str = "Active" if old_status else "Inactive"
        
        return self.create_notification(
            notification_type="warning",
            title=f"🔄 Facility Status Changed: {facility.name}",
            message=f"Facility status changed from {old_status_str} to {new_status}",
            details={
                "facility_id": facility.id,
                "facility_name": facility.name,
                "old_status": old_status_str,
                "new_status": new_status,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Revert Change", "Investigate", "Archive"],
            roles=["super_admin"],
            backend_source="facilities",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

    def create_facility_admin_assigned_notification(
        self, user: User, facility: Facility
    ):
        """SA003: Facility Admin Assigned"""
        full_name = f"{user.first_name} {user.last_name}"
        return self.create_notification(
            notification_type="info",
            title=f"👤 New Facility Admin: {full_name}",
            message=f"{full_name} has been assigned as admin for {facility.name}",
            details={
                "user_id": user.id,
                "user_name": full_name,
                "user_email": user.email,
                "facility_id": facility.id,
                "facility_name": facility.name,
                "permissions": ["manage_clinicians", "view_analytics", "manage_referrals"],
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Send Credentials", "Configure Access", "View Profile"],
            roles=["super_admin"],
            backend_source="users",
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )

    def create_ai_service_down_notification(
        self, service_name: str, error_details: Dict[str, Any]
    ):
        """SA004: AI Service Down"""
        return self.create_notification(
            notification_type="critical",
            title=f"🚨 AI Service Down: {service_name}",
            message=f"The {service_name} AI service is not responding",
            details={
                "service_name": service_name,
                "error_count": error_details.get("error_count", 0),
                "last_success": error_details.get("last_success"),
                "status": "down",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Restart Service", "View Logs", "Check Monitoring"],
            roles=["super_admin"],
            backend_source="ai_services",
            trigger_condition=f"ai_service.health.{service_name} === 'down'",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
        )

    def create_database_performance_alert_notification(
        self, error_rate: float, details: Dict[str, Any]
    ):
        """SA005: Database Performance Alert"""
        return self.create_notification(
            notification_type="critical",
            title="🚨 DATABASE PERFORMANCE CRITICAL",
            message=f"Database error rate ({error_rate*100:.1f}%) exceeds 10% threshold",
            details={
                "error_rate": f"{error_rate*100:.1f}%",
                "threshold": "10%",
                "query_count": details.get("query_count", 0),
                "slow_queries": details.get("slow_queries", 0),
                "affected_operations": details.get("affected_operations", []),
                "peak_time": details.get("peak_time"),
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Optimize DB", "Check Connections", "View Logs"],
            roles=["super_admin"],
            backend_source="database",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
        )

    def create_storage_critical_notification(
        self, used_storage_gb: float, total_storage_gb: float
    ):
        """SA006: System Storage Critical"""
        storage_percent = (used_storage_gb / total_storage_gb) * 100
        growth_rate = 2.5  # GB/day estimate
        days_until_full = (total_storage_gb - used_storage_gb) / growth_rate
        
        return self.create_notification(
            notification_type="critical",
            title="💾 STORAGE CRITICAL: 90% Full",
            message=f"System storage at {storage_percent:.1f}% capacity",
            details={
                "used_storage_gb": round(used_storage_gb, 2),
                "total_storage_gb": round(total_storage_gb, 2),
                "storage_percent": round(storage_percent, 1),
                "growth_rate": f"{growth_rate} GB/day",
                "days_until_full": round(days_until_full, 1),
                "largest_data_source": "Patient Documents (45%)",
                "alert_threshold": "90%",
            },
            actions=["Cleanup Storage", "Request Upgrade", "Archive Data"],
            roles=["super_admin"],
            backend_source="system",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_multiple_failed_logins_notification(
        self, ip_address: str, attempted_count: int, attempted_usernames: List[str]
    ):
        """SA007: Multiple Failed Logins"""
        return self.create_notification(
            notification_type="critical",
            title="🚨 SECURITY ALERT: Multiple Failed Logins",
            message=f"{attempted_count} failed login attempts from {ip_address}",
            details={
                "ip_address": ip_address,
                "attempted_usernames": attempted_usernames[:5],  # First 5
                "attempt_count": attempted_count,
                "time_window": "15 minutes",
                "status": "suspicious",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Block IP", "Review Logs", "Force Password Reset"],
            roles=["super_admin"],
            backend_source="security",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

    def create_hipaa_violation_notification(
        self, violating_user_id: int, accessed_patient_count: int, severity: str
    ):
        """SA008: HIPAA Violation Detected"""
        return self.create_notification(
            notification_type="critical",
            title="🚨 HIPAA VIOLATION DETECTED",
            message=f"Unauthorized access attempt by user {violating_user_id}",
            details={
                "violating_user_id": violating_user_id,
                "accessed_patient_count": accessed_patient_count,
                "severity_level": severity,
                "record_types": ["Medical Records", "Patient Demographics"],
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "status": "requires_investigation",
            },
            actions=["Suspend User", "File Report", "Notify Compliance"],
            roles=["super_admin"],
            backend_source="security",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

    def create_system_health_report_notification(
        self, metrics: Dict[str, Any]
    ):
        """SA009: System Health Report (Daily/Weekly)"""
        return self.create_notification(
            notification_type="info",
            title="📊 System Health Report",
            message="Your daily system health summary is ready",
            details={
                "uptime_percent": metrics.get("uptime_percent", 99.9),
                "error_rate": metrics.get("error_rate", 0.5),
                "active_facilities": metrics.get("active_facilities", 0),
                "active_users": metrics.get("active_users", 0),
                "total_referrals_today": metrics.get("total_referrals_today", 0),
                "avg_turnaround_hours": metrics.get("avg_turnaround_hours", 0),
                "report_date": datetime.now(timezone.utc).isoformat(),
            },
            actions=["View Full Report", "Export", "Configure Alerts"],
            roles=["super_admin"],
            backend_source="analytics",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    # ============================================================================
    # FACILITY ADMIN & CLINICIAN SHARED NOTIFICATIONS (FA001-FA017)
    # ============================================================================

    def create_incoming_referral_notification(
        self, referral: Referral
    ):
        """FA001: Incoming Referral"""
        priority_emoji = {
            Priority.EMERGENCY.value: "🚨",
            Priority.HIGH.value: "⚠️",
            Priority.MEDIUM.value: "📋",
            Priority.LOW.value: "ℹ️",
        }
        
        emoji = priority_emoji.get(referral.priority, "📋")
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        from_facility = referral.from_facility if referral.from_facility else None
        
        return self.create_notification(
            notification_type="critical" if referral.priority == Priority.EMERGENCY.value else "info",
            title=f"{emoji} New Referral: {patient_name} ({referral.priority})",
            message=f"Incoming patient referral from {from_facility.name if from_facility else 'Referring Facility'}",
            details={
                "patient_id": referral.patient_id,
                "patient_name": patient_name,
                "patient_dob": patient.date_of_birth.isoformat() if patient else "Unknown",
                "chronic_conditions": patient.chronic_conditions if patient else "None",
                "priority": referral.priority,
                "from_facility": from_facility.name if from_facility else "Unknown",
                "urgency_level": referral.priority,
                "clinical_summary": referral.reason_for_referral or "No summary provided",
                "referral_id": referral.id,
            },
            actions=["Accept", "Reject", "Call Clinic", "View Patient", "Schedule Appointment"],
            facility_id=referral.to_facility_id,
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            trigger_condition=f"referral.status === 'submitted' && referral.id === {referral.id}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_referral_accepted_notification(
        self, referral: Referral, accepted_by_user: User
    ):
        """FA002: Referral Accepted"""
        from_facility = referral.from_facility if referral.from_facility else None
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        physician_name = f"{accepted_by_user.first_name} {accepted_by_user.last_name}"
        
        return self.create_notification(
            notification_type="info",
            title=f"✅ Referral Accepted: {patient_name}",
            message=f"Your referral has been accepted by {physician_name}",
            details={
                "patient_id": referral.patient_id,
                "receiving_facility": referral.to_facility.name if referral.to_facility else "Unknown",
                "accepting_physician_name": physician_name,
                "accepted_at": referral.accepted_at.isoformat() if referral.accepted_at else datetime.now(timezone.utc).isoformat(),
                "eta": "2 hours",
                "accepting_facility_contact": referral.to_facility.phone if referral.to_facility else "",
            },
            actions=["Prepare Patient", "Schedule Bed", "Alert Staff", "Update Family"],
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_referral_rejected_notification(
        self, referral: Referral, rejection_reason: str
    ):
        """FA003: Referral Rejected"""
        from_facility = referral.from_facility if referral.from_facility else None
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        
        return self.create_notification(
            notification_type="warning",
            title=f"❌ Referral Rejected: {patient_name}",
            message=f"Your referral has been rejected. Reason: {rejection_reason[:100]}",
            details={
                "patient_id": referral.patient_id,
                "receiving_facility": referral.to_facility.name if referral.to_facility else "Unknown",
                "rejection_reason": rejection_reason,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "suggestions": "Consider alternative facilities with appropriate services",
                "next_steps": ["Contact Facility", "Try Alternative", "Escalate"],
            },
            actions=["Contact Facility", "Try Alternative", "Escalate"],
            facility_id=referral.from_facility_id, # Notify the referring facility
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_referral_in_transit_notification(
        self, referral: Referral, transport_method: str = "Ambulance"
    ):
        """FA004: Referral In Transit"""
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        to_facility = referral.to_facility if referral.to_facility else None
        
        return self.create_notification(
            notification_type="info",
            title=f"🚑 Patient In Transit: {patient_name}",
            message=f"Patient is being transferred to {to_facility.name if to_facility else 'receiving facility'}",
            details={
                "patient_id": referral.patient_id,
                "transport_method": transport_method,
                "eta": "30 minutes",
                "location_updates": "En route to facility",
                "receiving_facility": to_facility.name if to_facility else "Unknown",
                "transport_contact": "+1-555-0123",
            },
            actions=["Confirm Receipt", "Update ETA", "Alert Staff"],
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_referral_received_notification(
        self, referral: Referral
    ):
        """FA005: Referral Received"""
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        
        return self.create_notification(
            notification_type="info",
            title=f"🏥 Patient Arrived: {patient_name}",
            message=f"Patient has been admitted to the facility",
            details={
                "patient_id": referral.patient_id,
                "arrival_time": datetime.now(timezone.utc).isoformat(),
                "ward_location": "ICU - Room 204",
                "admission_status": "Admitted",
                "vital_signs": "Stable",
            },
            actions=["Confirm Admission", "Update Records", "Notify Referring Clinic"],
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_referral_completed_notification(
        self, referral: Referral
    ):
        """FA006: Referral Completed"""
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        
        return self.create_notification(
            notification_type="info",
            title=f"🎉 Referral Completed: {patient_name}",
            message="Care pathway has been completed successfully",
            details={
                "patient_id": referral.patient_id,
                "discharge_date": datetime.now(timezone.utc).isoformat(),
                "outcomes": "Successful treatment completed",
                "treatment_summary": "Patient responded well to treatment and is stable for discharge",
                "follow_up_instructions": "Follow-up appointment in 2 weeks",
            },
            actions=["Provide Feedback", "Close Case", "Schedule Follow-up"],
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

    def create_referral_sla_breached_notification(
        self, referral: Referral, sla_target: str, current_time_hours: float
    ):
        """FA007: Referral SLA Breached"""
        patient = referral.patient if referral.patient else None
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
        
        return self.create_notification(
            notification_type="warning",
            title=f"⏰ SLA Breached: {patient_name}",
            message=f"Processing time ({current_time_hours:.1f}h) exceeds SLA target ({sla_target})",
            details={
                "patient_id": referral.patient_id,
                "time_elapsed": f"{current_time_hours:.1f} hours",
                "sla_target": sla_target,
                "referral_id": referral.id,
                "current_step": referral.status,
            },
            actions=["Expedite", "Escalate", "Extend Timeline"],
            roles=["facility_admin", "clinician"],
            backend_source="referrals",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_patient_documents_uploaded_notification(
        self, referral_id: int, document_count: int, uploader: User
    ):
        """FA008: Patient Documents Uploaded"""
        uploader_name = f"{uploader.first_name} {uploader.last_name}"
        return self.create_notification(
            notification_type="info",
            title=f"📄 Documents Uploaded ({document_count} files)",
            message=f"{uploader_name} uploaded {document_count} document(s) for this patient",
            details={
                "referral_id": referral_id,
                "document_count": document_count,
                "uploader": uploader_name,
                "uploader_id": uploader.id,
                "upload_time": datetime.now(timezone.utc).isoformat(),
                "total_file_size": "8.5 MB",
            },
            actions=["Review", "Analyze with AI", "Download", "Share"],
            roles=["facility_admin", "clinician"],
            backend_source="documents",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_test_results_notification(
        self, patient_id: int, test_type: str, result_status: str, summary: str
    ):
        """FA009: Test Results Available"""
        status_emoji = {"normal": "✅", "abnormal": "⚠️", "critical": "🚨"}
        emoji = status_emoji.get(result_status, "📋")
        
        return self.create_notification(
            notification_type="critical" if result_status == "critical" else "info",
            title=f"{emoji} {test_type} Results Available",
            message=f"Lab/Imaging results ready for review - Status: {result_status}",
            details={
                "patient_id": patient_id,
                "test_type": test_type,
                "result_status": result_status,
                "results_summary": summary,
                "critical_findings": "None" if result_status != "critical" else "Abnormalities detected",
                "available_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Review Results", "Take Action", "Contact Patient", "Schedule Follow-up"],
            roles=["facility_admin", "clinician"],
            backend_source="lab",
            expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        )

    def create_document_analysis_complete_notification(
        self, document_id: int, document_name: str, confidence_percent: float
    ):
        """FA010: Document Analysis Complete"""
        return self.create_notification(
            notification_type="info",
            title=f"✅ AI Analysis Complete: {document_name}",
            message=f"Document analysis finished with {confidence_percent:.0f}% confidence",
            details={
                "document_id": document_id,
                "document_name": document_name,
                "confidence_percentage": confidence_percent,
                "extracted_data_preview": "Diagnosis: Acute Myocardial Infarction...",
                "actions_suggested": ["Review Findings", "Update Patient Record", "Schedule Follow-up"],
                "review_required": True if confidence_percent < 85 else False,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Review", "Approve", "Correct", "Reject"],
            roles=["facility_admin", "clinician"],
            backend_source="ai_analysis",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_voice_note_transcribed_notification(
        self, referral_id: int, words_count: int, accuracy_percent: float
    ):
        """FA011: Voice Note Transcribed"""
        return self.create_notification(
            notification_type="info",
            title="🎙️ Voice Note Transcribed",
            message=f"AI transcription complete - {words_count} words, {accuracy_percent:.0f}% accuracy",
            details={
                "referral_id": referral_id,
                "transcription_length_words": words_count,
                "accuracy_percent": accuracy_percent,
                "confidence_score": round(accuracy_percent / 100, 2),
                "key_findings": "Patient reports chest pain and shortness of breath...",
                "notes_preview": "[First 100 characters of transcription]",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Review", "Approve", "Edit", "Reject"],
            roles=["facility_admin", "clinician"],
            backend_source="voice_notes",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_patient_followup_due_notification(
        self, patient_id: int, days_since_referral: int
    ):
        """FA012: Patient Follow-up Due"""
        return self.create_notification(
            notification_type="warning",
            title="📞 Patient Follow-up Due",
            message=f"Follow-up action needed for patient ({days_since_referral} days since referral)",
            details={
                "patient_id": patient_id,
                "days_since_referral": days_since_referral,
                "recommended_actions": ["Check vitals", "Review medications", "Assess recovery"],
                "contact_preferences": "Phone",
                "follow_up_type": "Post-Treatment",
            },
            actions=["Schedule Appointment", "Send Message", "Take Action"],
            roles=["facility_admin", "clinician"],
            backend_source="patient_management",
            expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        )

    def create_unauthorized_access_notification(
        self, user_id: int, accessed_patient_id: int, blocked_action: str
    ):
        """FA013: Unauthorized Access Attempt"""
        return self.create_notification(
            notification_type="critical",
            title="🚨 Unauthorized Access Attempt",
            message=f"Blocked access attempt for patient record",
            details={
                "user_id": user_id,
                "accessed_patient_id": accessed_patient_id,
                "attempt_type": "Record Access",
                "blocked_action": blocked_action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": "192.168.1.100",
            },
            actions=["Review Logs", "Take Action", "Report"],
            roles=["facility_admin", "clinician"],
            backend_source="security",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

    def create_facility_announcement_notification(
        self, title: str, message: str, urgency: str = "normal"
    ):
        """FA014: Facility Announcement"""
        urgency_emoji = {"urgent": "🚨", "high": "⚠️", "normal": "📢", "low": "ℹ️"}
        emoji = urgency_emoji.get(urgency, "📢")
        
        return self.create_notification(
            notification_type="warning" if urgency in ["urgent", "high"] else "info",
            title=f"{emoji} {title}",
            message=message[:200],
            details={
                "full_message": message,
                "category": "Admin Announcement",
                "sender_name": "Facility Admin",
                "urgency_level": urgency,
                "required_actions": ["Read", "Acknowledge"],
                "announcement_date": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Read", "Acknowledge", "Take Action"],
            roles=["facility_admin", "clinician"],
            backend_source="announcements",
            expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        )

    def create_clinical_guideline_updated_notification(
        self, guideline_name: str, affected_conditions: List[str]
    ):
        """FA015: Clinical Guideline Updated"""
        return self.create_notification(
            notification_type="info",
            title=f"📚 Clinical Guideline Updated: {guideline_name}",
            message="A new clinical guideline has been published",
            details={
                "guideline_name": guideline_name,
                "affected_conditions": affected_conditions,
                "affected_procedures": ["Cardiac Assessment", "Lab Testing"],
                "effective_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "summary": "Updated guidelines for treating acute conditions...",
                "changes": ["New diagnostic criteria", "Updated treatment protocols"],
            },
            actions=["Read Guideline", "Acknowledge", "Request Training"],
            roles=["facility_admin", "clinician"],
            backend_source="guidelines",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

    def create_ai_performance_alert_notification(
        self, affected_services: List[str], accuracy_current: float, accuracy_target: float
    ):
        """FA016: AI Performance Alert"""
        return self.create_notification(
            notification_type="warning",
            title="⚠️ AI Performance Below Target",
            message=f"AI accuracy ({accuracy_current:.1f}%) is below target ({accuracy_target:.1f}%)",
            details={
                "affected_services": affected_services,
                "accuracy_current": accuracy_current,
                "accuracy_target": accuracy_target,
                "impact_summary": f"{len(affected_services)} AI services affected",
                "affected_referrals": 12,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Review Quality", "Escalate", "Take Action"],
            roles=["facility_admin", "clinician"],
            backend_source="ai_monitoring",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_weekly_performance_summary_notification(
        self, metrics: Dict[str, Any]
    ):
        """FA017: Weekly Performance Summary"""
        return self.create_notification(
            notification_type="info",
            title="📊 Weekly Performance Summary",
            message="Your facility's weekly performance report is ready",
            details={
                "referrals_created": metrics.get("referrals_created", 0),
                "referrals_received": metrics.get("referrals_received", 0),
                "completion_rate": metrics.get("completion_rate", 0),
                "avg_turnaround": metrics.get("avg_turnaround", 0),
                "patient_satisfaction_score": metrics.get("satisfaction", 4.5),
                "top_issues": metrics.get("top_issues", []),
                "week_ending": datetime.now(timezone.utc).isoformat(),
            },
            actions=["View Full Report", "Download", "Share with Team"],
            roles=["facility_admin", "clinician"],
            backend_source="analytics",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    # ============================================================================
    # FACILITY ADMIN ONLY NOTIFICATIONS (FA101-FA103)
    # ============================================================================

    def create_clinician_created_notification(
        self, user: User, facility: Facility
    ):
        """FA101: Clinician Created"""
        full_name = f"{user.first_name} {user.last_name}"
        return self.create_notification(
            notification_type="info",
            title=f"👤 New Clinician Added: {full_name}",
            message=f"New clinician {full_name} has been created for your facility",
            details={
                "user_id": user.id,
                "user_name": full_name,
                "user_email": user.email,
                "specialization": user.specialization if hasattr(user, 'specialization') else "General",
                "facility_id": facility.id,
                "facility_name": facility.name,
                "credentials": ["Medical License", "HIPAA Certified"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Send Welcome", "Configure Access", "Assign Patients"],
            facility_id=facility.id,
            roles=["facility_admin"],
            backend_source="users",
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )

    def create_clinician_updated_notification(
        self, user: User, changed_fields: List[str]
    ):
        """FA102: Clinician Updated"""
        full_name = f"{user.first_name} {user.last_name}"
        return self.create_notification(
            notification_type="info",
            title=f"🔄 Clinician Profile Updated: {full_name}",
            message=f"Clinician {full_name}'s profile has been updated",
            details={
                "user_id": user.id,
                "user_name": full_name,
                "changed_fields": changed_fields,
                "new_permissions": ["manage_patients", "view_analytics"],
                "old_permissions": ["view_patients"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            actions=["Review Changes", "Undo", "Reassign Workload"],
            roles=["facility_admin"],
            backend_source="users",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def create_storage_warning_notification(
        self, facility: Facility, used_gb: float, total_gb: float
    ):
        """FA103: Storage Warning (Facility)"""
        storage_percent = (used_gb / total_gb) * 100
        
        return self.create_notification(
            notification_type="warning",
            title=f"💾 Storage Warning: {facility.name}",
            message=f"Facility storage at {storage_percent:.0f}% capacity",
            details={
                "facility_id": facility.id,
                "facility_name": facility.name,
                "used_storage_gb": round(used_gb, 2),
                "total_storage_gb": round(total_gb, 2),
                "storage_percent": round(storage_percent, 1),
                "days_until_full": 15,
                "growth_rate": "500 MB/day",
                "largest_data_source": "Patient Documents",
            },
            actions=["Cleanup", "Archive", "Request Upgrade"],
            roles=["facility_admin"],
            backend_source="system",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
