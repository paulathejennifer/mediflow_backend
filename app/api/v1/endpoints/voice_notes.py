from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.utils.file_utils import AudioHandler
from app.utils.audit_utils import create_audit_logger
from app.schemas.voice_note import VoiceNoteResponse, VoiceNoteSummary, VoiceNoteUpdate
from app.models.voice_note import VoiceNote
from app.models.referral import Referral
from app.models.user import User
from app.enums import UserRole, AuditAction, VoiceStatus

router = APIRouter()

@router.post("/upload", response_model=VoiceNoteResponse)
def upload_voice_note(
    referral_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a voice note for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)
    
    # Verify referral exists
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found"
        )
    
    try:
        # Handle audio file upload
        audio_handler = AudioHandler()
        audio_metadata = await audio_handler.handle_upload(file, referral_id, current_user.id)
        
        # Create voice note record
        voice_note = VoiceNote(
            referral_id=referral_id,
            uploaded_by=current_user.id,
            status=VoiceStatus.UPLOADED,
            **audio_metadata
        )
        
        db.add(voice_note)
        db.commit()
        db.refresh(voice_note)
        
        # Log upload
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPLOAD,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details={
                "referral_id": referral_id,
                "file_name": file.filename,
                "file_size": audio_metadata["audio_file_size"]
            }
        )
        
        return voice_note
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload voice note: {str(e)}"
        )

@router.get("/referral/{referral_id}", response_model=List[VoiceNoteSummary])
def list_referral_voice_notes(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List voice notes for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)
    
    voice_notes = db.query(VoiceNote).filter(
        VoiceNote.referral_id == referral_id
    ).order_by(VoiceNote.created_at.desc()).all()
    
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
            uploader_name=f"{uploader.first_name} {uploader.last_name}" if uploader else "Unknown"
        )
        result.append(summary)
    
    return result

@router.get("/{voice_note_id}", response_model=VoiceNoteResponse)
def get_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get voice note by ID."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice note not found"
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
    current_user: User = Depends(get_current_user)
):
    """Update voice note (typically for AI processing results)."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice note not found"
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
            action=AuditAction.UPDATE,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details=update_data
        )
        
        return voice_note
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update voice note: {str(e)}"
        )

@router.delete("/{voice_note_id}")
def delete_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a voice note."""
    voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice note not found"
        )
    
    # Check permissions - only uploader or admin can delete
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(voice_note.referral_id)
    
    if (voice_note.uploaded_by != current_user.id and 
        current_user.role not in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only voice note uploader or admin can delete voice notes"
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
            action=AuditAction.DELETE,
            entity_type="voice_note",
            entity_id=voice_note.id,
            details={
                "file_name": voice_note.audio_file_name,
                "referral_id": voice_note.referral_id
            }
        )
        
        return {"message": "Voice note deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete voice note: {str(e)}"
        )
