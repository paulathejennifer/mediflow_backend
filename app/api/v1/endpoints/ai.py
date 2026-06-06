"""
AI Endpoints for Mediflow System

This module provides API endpoints for AI operations including:
- Manual AI testing during development
- AI-powered insights generation
- AI status monitoring
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.services.ai_service import AIService
from app.models.referral import Referral
from app.models.user import User
from app.enums import UserRole

router = APIRouter()


class ReferralSummaryRequest(BaseModel):
    """Request model for referral summary generation."""

    patient_name: str
    age: Optional[str] = "Unknown"
    gender: Optional[str] = "Unknown"
    date_of_birth: Optional[str] = "Unknown"
    allergies: Optional[str] = "None documented"
    medications: Optional[str] = "None documented"
    chronic_conditions: Optional[str] = "None documented"
    reason_for_referral: str
    priority: Optional[str] = "medium"
    from_facility: Optional[str] = "Unknown"
    to_facility: Optional[str] = "Unknown"
    clinical_notes: Optional[str] = "No clinical notes provided"
    documents_summary: Optional[str] = "No documents attached"
    voice_transcripts: Optional[str] = "No voice notes provided"
    created_at: Optional[str] = ""
    status: Optional[str] = "Unknown"


class TranscriptionCleanupRequest(BaseModel):
    """Request model for transcription cleanup."""

    raw_transcript: str
    patient_name: Optional[str] = "Unknown"
    referral_reason: Optional[str] = "Unknown"
    specialty: Optional[str] = "General"


class DocumentExtractionRequest(BaseModel):
    """Request model for document information extraction."""

    document_type: str
    document_text: str
    patient_name: Optional[str] = "Unknown"
    age: Optional[str] = "Unknown"
    gender: Optional[str] = "Unknown"


@router.post("/test-summary")
async def test_referral_summary(
    request: ReferralSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test AI referral summary generation.

    This endpoint is useful during development to test AI capabilities
    without requiring a full referral workflow.
    """
    # Check permissions - only clinicians and admins can test AI
    permission_checker = get_permission_checker(current_user, db)
    if current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
        UserRole.CLINICIAN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for AI testing",
        )

    try:
        ai_service = AIService(db)

        # Build context for AI
        context = {
            "patient_name": request.patient_name,
            "age": request.age,
            "gender": request.gender,
            "date_of_birth": request.date_of_birth,
            "allergies": request.allergies,
            "medications": request.medications,
            "chronic_conditions": request.chronic_conditions,
            "reason_for_referral": request.reason_for_referral,
            "priority": request.priority,
            "from_facility": request.from_facility,
            "to_facility": request.to_facility,
            "clinical_notes": request.clinical_notes,
            "documents_summary": request.documents_summary,
            "voice_transcripts": request.voice_transcripts,
            "created_at": request.created_at,
            "status": request.status,
        }

        # Generate AI summary
        summary_result = await ai_service.generate_referral_summary(context)

        return {
            "success": True,
            "context": context,
            "ai_summary": summary_result,
            "tested_by": current_user.email,
            "test_timestamp": str(db.query(func.now()).scalar()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI summary generation failed: {str(e)}",
        )


@router.post("/test-transcription")
async def test_transcription_cleanup(
    request: TranscriptionCleanupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test AI transcription cleanup.

    This endpoint is useful for testing voice-to-text cleanup capabilities.
    """
    # Check permissions
    permission_checker = get_permission_checker(current_user, db)
    if current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
        UserRole.CLINICIAN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for AI testing",
        )

    try:
        ai_service = AIService(db)

        # Build context for AI
        context = {
            "raw_transcript": request.raw_transcript,
            "patient_name": request.patient_name,
            "referral_reason": request.referral_reason,
            "specialty": request.specialty,
        }

        # Clean transcription
        cleanup_result = await ai_service.clean_transcription(context)

        return {
            "success": True,
            "context": context,
            "cleaned_transcript": cleanup_result,
            "tested_by": current_user.email,
            "test_timestamp": str(db.query(func.now()).scalar()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription cleanup failed: {str(e)}",
        )


@router.post("/test-document-extraction")
async def test_document_extraction(
    request: DocumentExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test AI document information extraction.

    This endpoint is useful for testing document analysis capabilities.
    """
    # Check permissions
    permission_checker = get_permission_checker(current_user, db)
    if current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
        UserRole.CLINICIAN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for AI testing",
        )

    try:
        ai_service = AIService(db)

        # Build context for AI
        context = {
            "document_type": request.document_type,
            "document_text": request.document_text,
            "patient_name": request.patient_name,
            "age": request.age,
            "gender": request.gender,
        }

        # Extract document information
        extraction_result = await ai_service.extract_document_info(context)

        return {
            "success": True,
            "context": context,
            "extracted_info": extraction_result,
            "tested_by": current_user.email,
            "test_timestamp": str(db.query(func.now()).scalar()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document extraction failed: {str(e)}",
        )


@router.post("/referral/{referral_id}/summarize")
@router.post("/referral/{referral_id}/summarize/")
async def generate_referral_ai_summary(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate AI summary for an existing referral.

    This endpoint allows manual triggering of AI summarization
    for referrals that may not have been processed automatically.
    """
    # Check permissions
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    # Get referral
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    try:
        ai_service = AIService(db)

        # Build comprehensive context from referral
        from app.services.referral_service import ReferralService

        referral_service = ReferralService(db)
        # Removed await as get_referral_summary is synchronous with standard Session
        referral_summary = referral_service.get_referral_summary(referral_id) or {}

        # Build context for AI
        # Use .get() to prevent KeyErrors from crashing the 500
        patient_info = referral_summary.get("patient_info", {})
        referral_info = referral_summary.get("referral_info", {})
        facility_info = referral_summary.get("facility_info", {})
        attachments = referral_summary.get("attachments", {})

        context = {
            "patient_name": f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip()
            if patient_info
            else "Unknown",
            "age": referral_service._calculate_age(
                patient_info.get("date_of_birth")
            )
            if patient_info and patient_info.get("date_of_birth")
            else "Unknown",
            "gender": patient_info.get("gender")
            if patient_info
            else "Unknown",
            "allergies": patient_info.get("allergies")
            if patient_info
            else "None",
            "medications": patient_info.get("medications")
            if patient_info
            else "None",
            "chronic_conditions": patient_info.get("chronic_conditions")
            if patient_info
            else "None",
            "reason_for_referral": referral_info.get("reason_for_referral", "Not specified"),
            "priority": referral_info.get("priority", "medium"),
            "from_facility": facility_info.get("from_facility", {}).get("name")
            if facility_info.get("from_facility")
            else "Unknown",
            "to_facility": facility_info.get("to_facility", {}).get("name")
            if facility_info.get("to_facility")
            else "Unknown",
            "clinical_notes": referral_info.get("clinical_notes", ""),
            "documents_summary": referral_service._summarize_documents(
                attachments.get("documents", [])
            ) if attachments else "None",
            "voice_transcripts": referral_service._summarize_voice_notes(
                attachments.get("voice_notes", [])
            ) if attachments else "None",
            "created_at": (
                referral_info["created_at"].strftime("%Y-%m-%d %H:%M")
                if referral_info.get("created_at") and hasattr(referral_info["created_at"], "strftime")
                else str(referral_info.get("created_at", "Unknown"))
            ),
            "status": referral_info.get("status", "Unknown"),
        }

        # Generate AI summary
        summary_result = await ai_service.generate_referral_summary(context)

        # Update referral with AI summary
        # Save the whole dictionary as JSON so we don't lose key findings/risks
        if isinstance(summary_result, dict):
            referral.ai_summary = json.dumps(summary_result)
        else:
            referral.ai_summary = str(summary_result)
        referral.ai_status = "completed"
        db.commit()

        return {
            "success": True,
            "referral_id": referral_id,
            "ai_summary": summary_result,
            "updated_by": current_user.email,
            "updated_at": str(db.query(func.now()).scalar()),
        }
    except Exception as e:
        # Log the actual error to Render console so you can see what failed
        print(f"CRITICAL AI ERROR for referral {referral_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI summary generation failed: {str(e)}",
        )


@router.get("/status")
def get_ai_status(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get AI service status and configuration.

    This endpoint provides information about AI capabilities
    and current configuration for monitoring purposes.
    """
    # Check permissions - admins only
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for AI status",
        )

    try:
        from app.core.config import settings

        # Check AI service availability
        ai_service = AIService(db)

        status_info = {
            "ai_service_available": True,
            "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
            "whisper_model": settings.WHISPER_MODEL,
            "supported_operations": [
                "referral_summarization",
                "transcription_cleanup",
                "document_extraction",
                "missing_info_assessment",
                "risk_assessment",
            ],
            "prompt_templates_available": [
                "referral_summary",
                "transcription_cleanup",
                "document_extraction",
                "missing_info",
                "risk_assessment",
            ],
            "medical_safety_features": [
                "disclaimer_inclusion",
                "uncertainty_handling",
                "risk_flagging",
                "missing_info_identification",
            ],
            "service_dependencies": {
                "ai_service": "services/ai_service.py",
                "prompt_builder": "utils/ai_prompts.py",
                "text_cleaning": "utils/text_cleaning.py",
                "audio_processing": "utils/audio_utils.py",
            },
        }

        return status_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI status: {str(e)}",
        )


@router.get("/health")
def ai_health_check(db: Session = Depends(get_db)):
    """
    Simple health check for AI service.

    This endpoint can be used for monitoring and load balancing.
    """
    try:
        # Test basic AI service initialization
        ai_service = AIService(db)

        return {
            "status": "healthy",
            "service": "mediflow-ai",
            "timestamp": str(db.query(func.now()).scalar()),
            "mock_mode": not bool(ai_service.api_key),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unhealthy: {str(e)}",
        )
