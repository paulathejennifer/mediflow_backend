from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.services.voice_service import get_voice_service
from app.utils.audit_utils import create_audit_logger
from app.schemas.voice_note import VoiceNoteResponse, VoiceNoteSummary, VoiceNoteUpdate
from app.models.voice_note import VoiceNote
from app.models.referral import Referral
from app.models.user import User
from app.enums import UserRole, AuditAction, VoiceStatus

router = APIRouter()


@router.post("/transcribe-raw")
async def transcribe_raw_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transcribe audio without saving it to a referral (for preview during creation)."""
    try:
        from app.services.speech_ai_service import speech_ai_service
        import tempfile
        import os

        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 1. Get the raw text from Google
            speech_result = await speech_ai_service.transcribe_audio(tmp_path)
            raw_text = speech_result.get("transcript", "")
            
            if not raw_text:
                return speech_result

            # 2. Use Llama 3.1 to clean up medical terms and units (kg vs km)
            from app.services.ai_service import AIService
            ai_service = AIService(db)
            
            cleanup_result = await ai_service.clean_transcription({
                "raw_transcript": raw_text,
                "patient_name": "Patient", # Context is generic for previews
                "referral_reason": "Clinical Assessment",
                "specialty": "General Medicine"
            })
            
            polished_text = cleanup_result.get("cleaned_transcript", "")
            # Return the polished transcript
            return {
                "transcript": polished_text if polished_text and len(polished_text) > 0 else raw_text,
                "raw_transcript": raw_text,
                "corrections": cleanup_result.get("corrections", ""),
                "processing_info": speech_result.get("processing_info", {})
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.post("/upload", response_model=VoiceNoteResponse)
async def upload_voice_note(
    referral_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a voice note for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    # Verify referral exists
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    try:
        service = get_voice_service(db)
        voice_note = await service.upload_voice_note(
            referral_id=referral_id, 
            file=file, 
            uploader_id=current_user.id
        )

        # Log upload
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPLOAD.value,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details={
                "referral_id": referral_id,
                "file_name": file.filename,
                "file_size": voice_note.audio_file_size,
            },
        )

        return voice_note

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload voice note: {str(e)}",
        )


@router.get("/referral/{referral_id}", response_model=List[VoiceNoteSummary])
def list_referral_voice_notes(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List voice notes for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    voice_notes = (
        db.query(VoiceNote)
        .filter(VoiceNote.referral_id == referral_id)
        .order_by(VoiceNote.created_at.desc())
        .all()
    )

    # Create summaries with uploader names
    result = []
    for vn in voice_notes:
        uploader = db.query(User).filter(User.id == vn.uploaded_by).first()
        summary = VoiceNoteSummary(
            id=vn.id,
            audio_file_name=vn.audio_file_name,
            duration_seconds=vn.duration_seconds,
            status=vn.status,
            created_at=vn.created_at,
            uploader_name=f"{uploader.first_name} {uploader.last_name}"
            if uploader
            else "Unknown",
        )
        result.append(summary)

    return result


@router.get("/facility", response_model=List[VoiceNoteSummary])
def list_facility_voice_notes(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List all voice notes for the user's facility."""
    # Super Admin can see all voice notes
    if current_user.role == UserRole.SUPER_ADMIN:
        voice_notes = (
            db.query(VoiceNote)
            .order_by(VoiceNote.created_at.desc())
            .all()
        )
    else:
        if not current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with a facility",
            )

        # Get all referrals for this facility (both from and to)
        from app.models.referral import Referral

        referrals = (
            db.query(Referral)
            .filter(
                (Referral.from_facility_id == current_user.facility_id)
                | (Referral.to_facility_id == current_user.facility_id)
            )
            .all()
        )

        referral_ids = [r.id for r in referrals]

        # Get all voice notes for these referrals
        voice_notes = (
            db.query(VoiceNote)
            .filter(VoiceNote.referral_id.in_(referral_ids))
            .order_by(VoiceNote.created_at.desc())
            .all()
        )

    # Create summaries with uploader names
    result = []
    for vn in voice_notes:
        uploader = db.query(User).filter(User.id == vn.uploaded_by).first()
        summary = VoiceNoteSummary(
            id=vn.id,
            audio_file_name=vn.audio_file_name,
            duration_seconds=vn.duration_seconds,
            status=vn.status,
            created_at=vn.created_at,
            uploader_name=f"{uploader.first_name} {uploader.last_name}"
            if uploader
            else "Unknown",
        )
        result.append(summary)

    return result


@router.get("/{voice_note_id}", response_model=VoiceNoteResponse)
def get_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get voice note by ID."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(voice_note.referral_id)

    return voice_note


@router.put("/{voice_note_id}", response_model=VoiceNoteResponse)
def update_voice_note(
    voice_note_id: int,
    voice_note_update: VoiceNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update voice note (typically for AI processing results)."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(voice_note.referral_id)

    try:
        # Update fields
        update_data = voice_note_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(voice_note, field, value)

        db.commit()
        db.refresh(voice_note)

        # Log update
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE.value,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details=update_data,
        )

        return voice_note

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update voice note: {str(e)}",
        )


@router.post("/{voice_note_id}/transcribe")
async def transcribe_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transcribe a voice note using Whisper."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(voice_note.referral_id)

    try:
        from app.services.speech_ai_service import speech_ai_service

        # Transcribe audio
        transcription_result = await speech_ai_service.transcribe_audio(
            voice_note.audio_path
        )

        # Update voice note with transcript
        voice_note.transcript = transcription_result.get("transcript", "")
        voice_note.duration_seconds = transcription_result.get("duration_seconds")
        voice_note.status = VoiceStatus.TRANSCRIBED
        db.commit()
        db.refresh(voice_note)

        # Log transcription
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE.value,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details={
                "action": "transcribe",
                "duration_seconds": voice_note.duration_seconds,
                "word_count": transcription_result.get("word_count", 0),
                "confidence": transcription_result.get("confidence"),
            },
        )

        return {
            "voice_note_id": voice_note.id,
            "transcript": voice_note.transcript,
            "duration_seconds": voice_note.duration_seconds,
            "word_count": transcription_result.get("word_count", 0),
            "confidence": transcription_result.get("confidence"),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe voice note: {str(e)}",
        )


@router.post("/{voice_note_id}/summarize")
async def summarize_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI summary for a voice note transcript."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(voice_note.referral_id)

    if not voice_note.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice note must be transcribed before summarization",
        )

    try:
        from app.services.ai_service import AIService
        from app.models.referral import Referral
        from app.models.patient import Patient

        # Get referral and patient context
        referral = (
            db.query(Referral).filter(Referral.id == voice_note.referral_id).first()
        )
        patient = (
            db.query(Patient).filter(Patient.id == referral.patient_id).first()
            if referral
            else None
        )

        ai_service = AIService(db)

        # Build context for AI
        context = {
            "raw_transcript": voice_note.transcript,
            "patient_name": f"{patient.first_name} {patient.last_name}"
            if patient
            else "Unknown",
            "referral_reason": referral.reason_for_referral if referral else "Unknown",
            "specialty": "General",
        }

        # Clean and summarize transcript
        result = await ai_service.clean_transcription(context)
        cleaned_transcript = result.get("cleaned_transcript", "")

        # Update voice note with processed transcript
        voice_note.processed_transcript = cleaned_transcript
        voice_note.status = VoiceStatus.TRANSCRIBED
        db.commit()
        db.refresh(voice_note)

        return {
            "voice_note_id": voice_note.id,
            "processed_transcript": voice_note.processed_transcript,
            "original_transcript": voice_note.transcript,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize voice note: {str(e)}",
        )


@router.delete("/{voice_note_id}")
def delete_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a voice note."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
        )

    # Check permissions - only uploader or admin can delete
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(voice_note.referral_id)

    if voice_note.uploaded_by != current_user.id and current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only voice note uploader or admin can delete voice notes",
        )

    try:
        # Delete audio file from disk
        from app.utils.file_utils import FileUtils

        FileUtils.delete_file(voice_note.audio_path)

        # Delete database record
        db.delete(voice_note)
        db.commit()

        # Log deletion
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.DELETE.value,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details={
                "file_name": voice_note.audio_file_name,
                "referral_id": voice_note.referral_id,
            },
        )

        return {"message": "Voice note deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete voice note: {str(e)}",
        )
