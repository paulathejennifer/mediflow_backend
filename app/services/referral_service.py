"""
Referral Service for Mediflow System

This service handles referral-related business logic including:
- Referral creation and workflow management
- Status transitions
- AI summarization integration
- Referral analytics
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status
from app.models.referral import Referral
from app.models.patient import Patient
from app.models.facility import Facility
from app.models.user import User
from app.schemas.referral import ReferralCreate, ReferralUpdate
from app.services.ai_service import AIService
from app.enums import ReferralStatus, Priority, UserRole
from typing import List, Optional, Dict, Any
from datetime import datetime

class ReferralService:
    """Service for referral management operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def create_referral(self, referral_data: ReferralCreate, creator_id: int) -> Referral:
        """
        Create a new referral with validation and AI processing.
        
        Args:
            referral_data: Referral creation data
            creator_id: ID of user creating this referral
            
        Returns:
            Created referral object
        """
        # Verify patient exists
        patient = self.db.query(Patient).filter(Patient.id == referral_data.patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Verify to facility exists and is active
        to_facility = self.db.query(Facility).filter(
            and_(
                Facility.id == referral_data.to_facility_id,
                Facility.is_active == True
            )
        ).first()
        if not to_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination facility not found or inactive"
            )
        
        # Get creator's facility
        creator = self.db.query(User).filter(User.id == creator_id).first()
        if not creator or not creator.facility_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Creator must be assigned to a facility"
            )
        
        # Create referral
        referral = Referral(
            patient_id=referral_data.patient_id,
            from_facility_id=creator.facility_id,
            to_facility_id=referral_data.to_facility_id,
            created_by=creator_id,
            priority=referral_data.priority,
            reason_for_referral=referral_data.reason_for_referral,
            clinical_notes=referral_data.clinical_notes,
            status=ReferralStatus.DRAFT
        )
        
        self.db.add(referral)
        self.db.commit()
        self.db.refresh(referral)
        
        # Trigger AI processing asynchronously
        self._trigger_ai_processing(referral.id)
        
        return referral

    def get_referral_by_id(self, referral_id: int) -> Optional[Referral]:
        """Get referral by ID."""
        return self.db.query(Referral).filter(Referral.id == referral_id).first()

    def update_referral(self, referral_id: int, referral_update: ReferralUpdate, updater_id: int) -> Referral:
        """
        Update referral information with status validation.
        
        Args:
            referral_id: ID of referral to update
            referral_update: Update data
            updater_id: ID of user performing update
            
        Returns:
            Updated referral object
        """
        referral = self.get_referral_by_id(referral_id)
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral not found"
            )
        
        update_data = referral_update.dict(exclude_unset=True)
        
        # Validate status transitions
        if "status" in update_data:
            self._validate_status_transition(referral.status, update_data["status"], updater_id)
        
        # Apply updates
        for field, value in update_data.items():
            setattr(referral, field, value)
        
        self.db.commit()
        self.db.refresh(referral)
        
        # Re-trigger AI processing if clinical information changed
        if any(field in update_data for field in ["clinical_notes", "reason_for_referral"]):
            self._trigger_ai_processing(referral.id)
        
        return referral

    def submit_referral(self, referral_id: int, submitter_id: int) -> Referral:
        """
        Submit a draft referral.
        
        Args:
            referral_id: ID of referral to submit
            submitter_id: ID of user submitting referral
            
        Returns:
            Submitted referral object
        """
        referral = self.get_referral_by_id(referral_id)
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral not found"
            )
        
        if referral.status != ReferralStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft referrals can be submitted"
            )
        
        # Verify submitter is from sender facility
        submitter = self.db.query(User).filter(User.id == submitter_id).first()
        if not submitter or submitter.facility_id != referral.from_facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users from sender facility can submit referrals"
            )
        
        referral.status = ReferralStatus.SUBMITTED
        self.db.commit()
        self.db.refresh(referral)
        
        return referral

    def accept_referral(self, referral_id: int, accepter_id: int) -> Referral:
        """
        Accept a submitted referral.
        
        Args:
            referral_id: ID of referral to accept
            accepter_id: ID of user accepting referral
            
        Returns:
            Accepted referral object
        """
        referral = self.get_referral_by_id(referral_id)
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral not found"
            )
        
        if referral.status != ReferralStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted referrals can be accepted"
            )
        
        # Verify accepter is from receiver facility
        accepter = self.db.query(User).filter(User.id == accepter_id).first()
        if not accepter or accepter.facility_id != referral.to_facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users from receiver facility can accept referrals"
            )
        
        referral.status = ReferralStatus.ACCEPTED
        self.db.commit()
        self.db.refresh(referral)
        
        return referral

    def reject_referral(self, referral_id: int, rejecter_id: int, reason: str) -> Referral:
        """
        Reject a submitted referral.
        
        Args:
            referral_id: ID of referral to reject
            rejecter_id: ID of user rejecting referral
            reason: Reason for rejection
            
        Returns:
            Rejected referral object
        """
        referral = self.get_referral_by_id(referral_id)
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral not found"
            )
        
        if referral.status != ReferralStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted referrals can be rejected"
            )
        
        # Verify rejecter is from receiver facility
        rejecter = self.db.query(User).filter(User.id == rejecter_id).first()
        if not rejecter or rejecter.facility_id != referral.to_facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users from receiver facility can reject referrals"
            )
        
        referral.status = ReferralStatus.REJECTED
        referral.notes = f"Rejected: {reason}"
        self.db.commit()
        self.db.refresh(referral)
        
        return referral

    def get_facility_referrals(self, facility_id: int, role: str = "any", skip: int = 0, 
                             limit: int = 100, status: Optional[str] = None, 
                             priority: Optional[str] = None) -> List[Referral]:
        """
        Get referrals for a facility.
        
        Args:
            facility_id: Facility ID
            role: "sender", "receiver", or "any"
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            priority: Optional priority filter
            
        Returns:
            List of referrals
        """
        query = self.db.query(Referral)
        
        # Filter by facility role
        if role == "sender":
            query = query.filter(Referral.from_facility_id == facility_id)
        elif role == "receiver":
            query = query.filter(Referral.to_facility_id == facility_id)
        else:  # "any"
            query = query.filter(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id
                )
            )
        
        # Apply filters
        if status:
            query = query.filter(Referral.status == status)
        
        if priority:
            query = query.filter(Referral.priority == priority)
        
        return query.order_by(Referral.created_at.desc()).offset(skip).limit(limit).all()

    def get_referral_summary(self, referral_id: int) -> Dict[str, Any]:
        """
        Get comprehensive referral summary with related data.
        
        Args:
            referral_id: Referral ID
            
        Returns:
            Dictionary with referral summary
        """
        referral = self.get_referral_by_id(referral_id)
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral not found"
            )
        
        # Get related data
        patient = self.db.query(Patient).filter(Patient.id == referral.patient_id).first()
        from_facility = self.db.query(Facility).filter(Facility.id == referral.from_facility_id).first()
        to_facility = self.db.query(Facility).filter(Facility.id == referral.to_facility_id).first()
        creator = self.db.query(User).filter(User.id == referral.created_by).first()
        
        # Get documents and voice notes
        from app.models.referral_document import ReferralDocument
        from app.models.voice_note import VoiceNote
        
        documents = self.db.query(ReferralDocument).filter(
            ReferralDocument.referral_id == referral_id
        ).all()
        
        voice_notes = self.db.query(VoiceNote).filter(
            VoiceNote.referral_id == referral_id
        ).all()
        
        return {
            "referral_info": {
                "id": referral.id,
                "status": referral.status,
                "priority": referral.priority,
                "reason_for_referral": referral.reason_for_referral,
                "clinical_notes": referral.clinical_notes,
                "ai_summary": referral.ai_summary,
                "notes": referral.notes,
                "created_at": referral.created_at,
                "updated_at": referral.updated_at
            },
            "patient_info": {
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": patient.date_of_birth,
                "gender": patient.gender,
                "allergies": patient.allergies,
                "medications": patient.medications,
                "chronic_conditions": patient.chronic_conditions
            } if patient else None,
            "facility_info": {
                "from_facility": {
                    "id": from_facility.id,
                    "name": from_facility.name,
                    "facility_code": from_facility.facility_code
                } if from_facility else None,
                "to_facility": {
                    "id": to_facility.id,
                    "name": to_facility.name,
                    "facility_code": to_facility.facility_code
                } if to_facility else None
            },
            "creator_info": {
                "id": creator.id,
                "first_name": creator.first_name,
                "last_name": creator.last_name,
                "role": creator.role
            } if creator else None,
            "attachments": {
                "documents": [
                    {
                        "id": doc.id,
                        "file_name": doc.file_name,
                        "file_type": doc.file_type,
                        "file_size": doc.file_size,
                        "created_at": doc.created_at
                    }
                    for doc in documents
                ],
                "voice_notes": [
                    {
                        "id": vn.id,
                        "audio_file_name": vn.audio_file_name,
                        "duration_seconds": vn.duration_seconds,
                        "status": vn.status,
                        "created_at": vn.created_at
                    }
                    for vn in voice_notes
                ]
            }
        }

    def get_referral_analytics(self, facility_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get referral analytics for a facility.
        
        Args:
            facility_id: Facility ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with referral analytics
        """
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query for facility referrals
        base_query = self.db.query(Referral).filter(
            and_(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id
                ),
                Referral.created_at >= start_date
            )
        )
        
        total_referrals = base_query.count()
        
        # Sent vs received
        sent_referrals = base_query.filter(Referral.from_facility_id == facility_id).count()
        received_referrals = base_query.filter(Referral.to_facility_id == facility_id).count()
        
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
        
        # Average processing time (submitted to accepted)
        processing_times = []
        accepted_referrals = base_query.filter(
            and_(
                Referral.status == ReferralStatus.ACCEPTED,
                Referral.updated_at >= start_date
            )
        ).all()
        
        for referral in accepted_referrals:
            # This is simplified - in production, track actual status change timestamps
            processing_time = (referral.updated_at - referral.created_at).total_seconds() / 3600  # hours
            processing_times.append(processing_time)
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            "period_days": days,
            "total_referrals": total_referrals,
            "sent_referrals": sent_referrals,
            "received_referrals": received_referrals,
            "status_breakdown": status_breakdown,
            "priority_breakdown": priority_breakdown,
            "avg_processing_time_hours": round(avg_processing_time, 2),
            "acceptance_rate": (status_breakdown.get(ReferralStatus.ACCEPTED.value, 0) / max(status_breakdown.get(ReferralStatus.SUBMITTED.value, 1), 1)) * 100
        }

    def _validate_status_transition(self, current_status: str, new_status: str, user_id: int) -> None:
        """Validate that status transition is allowed."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Define valid transitions
        valid_transitions = {
            ReferralStatus.DRAFT: [ReferralStatus.SUBMITTED],
            ReferralStatus.SUBMITTED: [ReferralStatus.ACCEPTED, ReferralStatus.REJECTED],
            ReferralStatus.ACCEPTED: [ReferralStatus.IN_TRANSIT, ReferralStatus.REJECTED],
            ReferralStatus.IN_TRANSIT: [ReferralStatus.RECEIVED],
            ReferralStatus.RECEIVED: [ReferralStatus.COMPLETED],
            ReferralStatus.REJECTED: [],  # Terminal state
            ReferralStatus.COMPLETED: []  # Terminal state
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status} to {new_status}"
            )
        
        # Additional role-based validations
        if new_status == ReferralStatus.ACCEPTED and user.facility_id != self.get_referral_by_id(user_id).to_facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only receiving facility can accept referrals"
            )

    def _trigger_ai_processing(self, referral_id: int) -> None:
        """Trigger AI processing for referral (async)."""
        # In production, this would be a background task
        # For now, we'll trigger it synchronously for demonstration
        try:
            ai_service = AIService(self.db)
            referral_summary = self.get_referral_summary(referral_id)
            
            # Build context for AI
            context = {
                "patient_name": f"{referral_summary['patient_info']['first_name']} {referral_summary['patient_info']['last_name']}" if referral_summary['patient_info'] else "Unknown",
                "age": self._calculate_age(referral_summary['patient_info']['date_of_birth']) if referral_summary['patient_info'] and referral_summary['patient_info']['date_of_birth'] else "Unknown",
                "gender": referral_summary['patient_info']['gender'] if referral_summary['patient_info'] else "Unknown",
                "emergency_contact_name": referral_summary['patient_info'].get('emergency_contact_name', 'None') if referral_summary['patient_info'] else "None",
                "emergency_contact_phone": referral_summary['patient_info'].get('emergency_contact_phone', 'None') if referral_summary['patient_info'] else "None",
                "medical_history": referral_summary['patient_info'].get('medical_history', 'None') if referral_summary['patient_info'] else "None",
                "allergies": referral_summary['patient_info']['allergies'] if referral_summary['patient_info'] else "None",
                "medications": referral_summary['patient_info']['medications'] if referral_summary['patient_info'] else "None",
                "chronic_conditions": referral_summary['patient_info']['chronic_conditions'] if referral_summary['patient_info'] else "None",
                "reason_for_referral": referral_summary['referral_info']['reason_for_referral'],
                "priority": referral_summary['referral_info']['priority'],
                "from_facility": referral_summary['facility_info']['from_facility']['name'] if referral_summary['facility_info']['from_facility'] else "Unknown",
                "to_facility": referral_summary['facility_info']['to_facility']['name'] if referral_summary['facility_info']['to_facility'] else "Unknown",
                "clinical_notes": referral_summary['referral_info']['clinical_notes'],
                "documents_summary": self._summarize_documents(referral_summary['attachments']['documents']),
                "voice_transcripts": self._summarize_voice_notes(referral_summary['attachments']['voice_notes']),
                "created_at": referral_summary['referral_info']['created_at'].strftime("%Y-%m-%d %H:%M"),
                "status": referral_summary['referral_info']['status']
            }
            
            # Generate AI summary (async in production)
            import asyncio
            summary_result = asyncio.run(ai_service.generate_referral_summary(context))
            
            # Update referral with AI summary
            referral = self.get_referral_by_id(referral_id)
            referral.ai_summary = summary_result.get('summary', '')
            referral.ai_status = 'completed'
            self.db.commit()
            
        except Exception as e:
            # Log error but don't fail the referral creation
            print(f"AI processing failed for referral {referral_id}: {str(e)}")

    def _calculate_age(self, date_of_birth) -> int:
        """Calculate age from date of birth."""
        from datetime import datetime
        today = datetime.now().date()
        return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

    def _summarize_documents(self, documents: List[Dict]) -> str:
        """Summarize attached documents."""
        if not documents:
            return "No documents attached"
        
        summary = []
        for doc in documents:
            summary.append(f"- {doc['file_name']} ({doc['file_type']})")
        
        return "\n".join(summary)

    def _summarize_voice_notes(self, voice_notes: List[Dict]) -> str:
        """Summarize voice notes."""
        if not voice_notes:
            return "No voice notes"
        
        summary = []
        for vn in voice_notes:
            summary.append(f"- {vn['audio_file_name']} ({vn.get('duration_seconds', 'Unknown duration')}s)")
        
        return "\n".join(summary)

def get_referral_service(db: Session) -> ReferralService:
    """Get referral service instance."""
    return ReferralService(db)
