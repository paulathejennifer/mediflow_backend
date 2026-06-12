"""
Voice Service for Mediflow System

This service handles voice-related business logic including:
- Voice note upload and processing
- Audio transcription
- AI-powered transcript cleanup
- Audio file management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status, UploadFile
from app.models.voice_note import VoiceNote
from app.models.referral import Referral
from app.services.ai_service import AIService
from app.utils.s3_storage import s3_storage
from app.enums import VoiceStatus
from typing import List, Optional, Dict, Any
import os
import speech_recognition as sr


class VoiceService:
    """Service for voice note management operations."""

    def __init__(self, db: Session):
        self.db = db

    async def upload_voice_note(
        self, referral_id: int, file: UploadFile, uploader_id: int
    ) -> VoiceNote:
        """
        Upload and process a voice note for a referral.

        Args:
            referral_id: Referral ID
            file: Uploaded audio file
            uploader_id: ID of user uploading

        Returns:
            Created voice note object
        """
        # Verify referral exists
        referral = self.db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
            )

        try:
            # Handle audio file upload to Cloud Storage
            folder = f"referral_{referral_id}/voice_notes"
            meta = await s3_storage.upload_file(file, folder)

            # Create voice note record
            voice_note = VoiceNote(
                referral_id=referral_id,
                uploaded_by=uploader_id,
                status=VoiceStatus.UPLOADED,
                audio_path=meta["path"],
                audio_file_name=meta["name"],
                audio_file_size=meta["size"]
            )

            self.db.add(voice_note)
            self.db.commit()
            self.db.refresh(voice_note)

            # Trigger transcription processing
            # Run as a background task to prevent request timeouts
            asyncio.create_task(asyncio.to_thread(self._trigger_transcription, voice_note.id))

            return voice_note

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload voice note: {str(e)}",
            )

    def get_voice_note_by_id(self, voice_note_id: int) -> Optional[VoiceNote]:
        """Get voice note by ID."""
        return self.db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()

    def get_referral_voice_notes(
        self, referral_id: int, status: Optional[str] = None
    ) -> List[VoiceNote]:
        """
        Get voice notes for a referral.

        Args:
            referral_id: Referral ID
            status: Optional status filter

        Returns:
            List of voice notes
        """
        query = self.db.query(VoiceNote).filter(VoiceNote.referral_id == referral_id)

        if status:
            query = query.filter(VoiceNote.status == status)

        return query.order_by(VoiceNote.created_at.desc()).all()

    def update_voice_note(
        self,
        voice_note_id: int,
        transcript: str,
        processed_transcript: str = None,
        status: str = None,
        ai_summary: str = None,
    ) -> VoiceNote:
        """
        Update voice note with transcription results.

        Args:
            voice_note_id: Voice note ID
            transcript: Raw transcript
            processed_transcript: Cleaned transcript
            status: Processing status
            ai_summary: AI-generated summary

        Returns:
            Updated voice note object
        """
        voice_note = self.get_voice_note_by_id(voice_note_id)
        if not voice_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
            )

        voice_note.transcript = transcript
        if processed_transcript:
            voice_note.processed_transcript = processed_transcript
        if status:
            voice_note.status = status
        if ai_summary:
            voice_note.ai_summary = ai_summary

        self.db.commit()
        self.db.refresh(voice_note)

        return voice_note

    def delete_voice_note(self, voice_note_id: int, deleter_id: int) -> bool:
        """
        Delete a voice note with permission checks.

        Args:
            voice_note_id: Voice note ID
            deleter_id: ID of user deleting

        Returns:
            True if successful
        """
        voice_note = self.get_voice_note_by_id(voice_note_id)
        if not voice_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
            )

        # Check permissions (only uploader or admin can delete)
        from app.models.user import User
        from app.enums import UserRole

        deleter = self.db.query(User).filter(User.id == deleter_id).first()
        if not deleter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if voice_note.uploaded_by != deleter_id and deleter.role not in [
            UserRole.SUPER_ADMIN,
            UserRole.FACILITY_ADMIN,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only voice note uploader or admin can delete voice notes",
            )

        try:
            # Delete audio file from disk
            if os.path.exists(voice_note.audio_path):
                os.remove(voice_note.audio_path)

            # Delete database record
            self.db.delete(voice_note)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete voice note: {str(e)}",
            )

    def get_voice_note_summary(self, voice_note_id: int) -> Dict[str, Any]:
        """
        Get comprehensive voice note summary.

        Args:
            voice_note_id: Voice note ID

        Returns:
            Dictionary with voice note summary
        """
        voice_note = self.get_voice_note_by_id(voice_note_id)
        if not voice_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
            )

        # Get uploader info
        from app.models.user import User

        uploader = self.db.query(User).filter(User.id == voice_note.uploaded_by).first()

        # Get referral info
        referral = (
            self.db.query(Referral)
            .filter(Referral.id == voice_note.referral_id)
            .first()
        )

        return {
            "voice_note_info": {
                "id": voice_note.id,
                "audio_file_name": voice_note.audio_file_name,
                "audio_file_size": voice_note.audio_file_size,
                "duration_seconds": voice_note.duration_seconds,
                "status": voice_note.status,
                "created_at": voice_note.created_at,
            },
            "transcription_info": {
                "has_transcript": bool(voice_note.transcript),
                "transcript_length": len(voice_note.transcript)
                if voice_note.transcript
                else 0,
                "has_processed_transcript": bool(voice_note.processed_transcript),
                "processed_transcript_length": len(voice_note.processed_transcript)
                if voice_note.processed_transcript
                else 0,
                "ai_summary": voice_note.ai_summary,
            },
            "uploader_info": {
                "id": uploader.id,
                "name": f"{uploader.first_name} {uploader.last_name}"
                if uploader
                else "Unknown",
                "role": uploader.role if uploader else "Unknown",
            }
            if uploader
            else None,
            "referral_info": {
                "id": referral.id,
                "status": referral.status,
                "priority": referral.priority,
            }
            if referral
            else None,
        }

    def search_voice_notes(
        self, facility_id: int, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search voice notes by transcript content within a facility.

        Args:
            facility_id: Facility ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching voice notes with summaries
        """
        # Get referrals for this facility
        from app.models.referral import Referral

        referral_ids = (
            self.db.query(Referral.id)
            .filter(
                (Referral.from_facility_id == facility_id)
                | (Referral.to_facility_id == facility_id)
            )
            .subquery()
        )

        # Search voice notes
        search_term = f"%{query}%"
        voice_notes = (
            self.db.query(VoiceNote)
            .filter(
                and_(
                    VoiceNote.referral_id.in_(referral_ids),
                    VoiceNote.processed_transcript.ilike(search_term),
                )
            )
            .limit(limit)
            .all()
        )

        results = []
        for vn in voice_notes:
            results.append(
                {
                    "id": vn.id,
                    "audio_file_name": vn.audio_file_name,
                    "duration_seconds": vn.duration_seconds,
                    "created_at": vn.created_at,
                    "referral_id": vn.referral_id,
                    "matched_content": self._get_matched_content(
                        vn.processed_transcript, query
                    ),
                }
            )

        return results

    def get_voice_stats(self, facility_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get voice note statistics for a facility.

        Args:
            facility_id: Facility ID
            days: Number of days to analyze

        Returns:
            Dictionary with voice note statistics
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get referrals for this facility
        from app.models.referral import Referral

        referral_ids = (
            self.db.query(Referral.id)
            .filter(
                and_(
                    (Referral.from_facility_id == facility_id)
                    | (Referral.to_facility_id == facility_id),
                    Referral.created_at >= start_date,
                )
            )
            .subquery()
        )

        # Voice note statistics
        total_voice_notes = (
            self.db.query(VoiceNote)
            .filter(VoiceNote.referral_id.in_(referral_ids))
            .count()
        )

        # Status breakdown
        status_breakdown = {}
        for status in VoiceStatus:
            count = (
                self.db.query(VoiceNote)
                .filter(
                    and_(
                        VoiceNote.referral_id.in_(referral_ids),
                        VoiceNote.status == status.value,
                    )
                )
                .count()
            )
            status_breakdown[status.value] = count

        # Transcription stats
        transcribed_notes = (
            self.db.query(VoiceNote)
            .filter(
                and_(
                    VoiceNote.referral_id.in_(referral_ids),
                    VoiceNote.transcript.isnot(None),
                )
            )
            .count()
        )

        processed_notes = (
            self.db.query(VoiceNote)
            .filter(
                and_(
                    VoiceNote.referral_id.in_(referral_ids),
                    VoiceNote.processed_transcript.isnot(None),
                )
            )
            .count()
        )

        # Duration statistics
        total_duration = (
            self.db.query(func.sum(VoiceNote.duration_seconds))
            .filter(VoiceNote.referral_id.in_(referral_ids))
            .scalar()
            or 0
        )

        avg_duration = total_duration / max(total_voice_notes, 1)

        # Storage statistics
        total_size = (
            self.db.query(func.sum(VoiceNote.audio_file_size))
            .filter(VoiceNote.referral_id.in_(referral_ids))
            .scalar()
            or 0
        )

        return {
            "period_days": days,
            "total_voice_notes": total_voice_notes,
            "status_breakdown": status_breakdown,
            "transcribed_count": transcribed_notes,
            "transcription_rate": (transcribed_notes / max(total_voice_notes, 1)) * 100,
            "processed_count": processed_notes,
            "processing_rate": (processed_notes / max(total_voice_notes, 1)) * 100,
            "total_duration_minutes": round(total_duration / 60, 2),
            "avg_duration_seconds": round(avg_duration, 2),
            "total_storage_mb": round(total_size / (1024 * 1024), 2),
            "avg_file_size_mb": round(
                (total_size / max(total_voice_notes, 1)) / (1024 * 1024), 2
            ),
        }

    def _trigger_transcription(self, voice_note_id: int) -> None:
        """Trigger audio transcription (async)."""
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
            if not voice_note:
                return

            # Update status to processing
            voice_note.status = VoiceStatus.PROCESSING
            db.commit()

            # Perform transcription (mock implementation)
            transcript = self._transcribe_audio(voice_note)

            if transcript:
                # Update with raw transcript
                voice_note.transcript = transcript
                voice_note.status = VoiceStatus.TRANSCRIBED
                db.commit()

                # Trigger AI cleanup
                self._trigger_transcript_cleanup(voice_note_id, transcript)
        finally:
            db.close()
            
        except Exception as e:
            # Update status to failed
            voice_note = self.get_voice_note_by_id(voice_note_id)
            if voice_note:
                voice_note.status = VoiceStatus.FAILED
                self.db.commit()
            print(f"Transcription failed for voice note {voice_note_id}: {str(e)}")

    def _transcribe_audio(self, voice_note: VoiceNote) -> str:
        """Transcribe audio file using Google Speech Recognition."""
        try:
            # Initialize recognizer
            recognizer = sr.Recognizer()

            # Check if audio file exists
            if not os.path.exists(voice_note.audio_path):
                print(f"Audio file not found: {voice_note.audio_path}")
                return ""

            # Use the audio file
            with sr.AudioFile(voice_note.audio_path) as source:
                # Read the audio data
                audio_data = recognizer.record(source)

                # Recognize speech using Google's free web API
                try:
                    transcript = recognizer.recognize_google(audio_data)
                    return transcript
                except sr.UnknownValueError:
                    print(
                        f"Google Speech Recognition could not understand audio for {voice_note.audio_file_name}"
                    )
                    return ""
                except sr.RequestError as e:
                    print(
                        f"Could not request results from Google Speech Recognition service; {e}"
                    )
                    return ""

        except Exception as e:
            print(f"Error transcribing audio: {str(e)}")
            return ""

    def _trigger_transcript_cleanup(
        self, voice_note_id: int, raw_transcript: str
    ) -> None:
        """Trigger AI cleanup of transcript (async)."""
        try:
            voice_note = self.get_voice_note_by_id(voice_note_id)
            if not voice_note:
                return

            # Get referral context
            referral = (
                self.db.query(Referral)
                .filter(Referral.id == voice_note.referral_id)
                .first()
            )
            if not referral:
                return

            # Build context for AI cleanup
            context = {
                "raw_transcript": raw_transcript,
                "patient_name": "Patient",  # Would get from referral
                "referral_reason": referral.reason_for_referral,
                "specialty": "General",  # Would get from referral context
            }

                # Fix: Run cleanup in a task to avoid "run() cannot be called from a running loop"
            asyncio.create_task(self._run_async_cleanup(voice_note_id, context))

        except Exception as e:
            print(f"Transcript cleanup failed for voice note {voice_note_id}: {str(e)}")

    async def _run_async_cleanup(self, voice_note_id: int, context: Dict[str, Any]) -> None:
        """Background task for transcript cleanup with its own session."""
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            ai_service = AIService(db)
            cleanup_result = await ai_service.clean_transcription(context)
            
            voice_note = db.query(VoiceNote).filter(VoiceNote.id == voice_note_id).first()
            if voice_note:
                voice_note.processed_transcript = cleanup_result.get("cleaned_transcript", "")
                voice_note.ai_summary = cleanup_result.get("notes", "")
                voice_note.status = VoiceStatus.TRANSCRIBED.value
                db.commit()
        except Exception as e:
            print(f"Background cleanup failed: {e}")
        finally:
            db.close()

    def _get_matched_content(
        self, text: str, query: str, context_length: int = 100
    ) -> str:
        """Get context around matched query in text."""
        if not text or not query:
            return ""

        query_lower = query.lower()
        text_lower = text.lower()

        # Find first match
        match_index = text_lower.find(query_lower)
        if match_index == -1:
            return ""

        # Get context around match
        start = max(0, match_index - context_length)
        end = min(len(text), match_index + len(query) + context_length)

        context = text[start:end]
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        return context


def get_voice_service(db: Session) -> VoiceService:
    """Get voice service instance."""
    return VoiceService(db)
