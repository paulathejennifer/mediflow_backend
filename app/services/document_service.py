"""
Document Service for Mediflow System

This service handles document-related business logic including:
- Document upload and processing
- File type validation
- AI-powered text extraction
- Document management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status, UploadFile
from app.models.referral_document import ReferralDocument
from app.models.referral import Referral
from app.services.ai_service import AIService
from app.services.document_ai_service import DocumentAIService
from app.utils.s3_storage import s3_storage
from app.enums import DocumentType
from typing import List, Optional, Dict, Any
import os
import asyncio


class DocumentService:
    """Service for document management operations."""

    def __init__(self, db: Session):
        self.db = db

    async def upload_document(
        self, referral_id: int, file: UploadFile, file_type: str, uploader_id: int
    ) -> ReferralDocument:
        """
        Upload and process a document for a referral.

        Args:
            referral_id: Referral ID
            file: Uploaded file
            file_type: Type of document
            uploader_id: ID of user uploading

        Returns:
            Created document object
        """
        # Verify referral exists
        referral = self.db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
            )

        # Validate document type
        if file_type not in [dt.value for dt in DocumentType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type. Must be one of: {[dt.value for dt in DocumentType]}",
            )

        try:
            # Handle file upload to Cloud Storage
            folder = f"referral_{referral_id}/documents"
            file_metadata = await s3_storage.upload_file(file, folder)

            # Create document record
            document = ReferralDocument(
                referral_id=referral_id,
                uploaded_by=uploader_id,
                file_type=file_type,
                **file_metadata,
            )

            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)

            # Trigger AI processing for text extraction
            # Run as a background task so the API responds immediately
            asyncio.create_task(self._trigger_text_extraction(document.id))

            return document

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload document: {str(e)}",
            )

    def get_document_by_id(self, document_id: int) -> Optional[ReferralDocument]:
        """Get document by ID."""
        return (
            self.db.query(ReferralDocument)
            .filter(ReferralDocument.id == document_id)
            .first()
        )

    def get_referral_documents(
        self, referral_id: int, file_type: Optional[str] = None
    ) -> List[ReferralDocument]:
        """
        Get documents for a referral.

        Args:
            referral_id: Referral ID
            file_type: Optional file type filter

        Returns:
            List of documents
        """
        query = self.db.query(ReferralDocument).filter(
            ReferralDocument.referral_id == referral_id
        )

        if file_type:
            query = query.filter(ReferralDocument.file_type == file_type)

        return query.order_by(ReferralDocument.created_at.desc()).all()

    def delete_document(self, document_id: int, deleter_id: int) -> bool:
        """
        Delete a document with permission checks.

        Args:
            document_id: Document ID
            deleter_id: ID of user deleting

        Returns:
            True if successful
        """
        document = self.get_document_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Check permissions (only uploader or admin can delete)
        from app.models.user import User
        from app.enums import UserRole

        deleter = self.db.query(User).filter(User.id == deleter_id).first()
        if not deleter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if document.uploaded_by != deleter_id and deleter.role not in [
            UserRole.SUPER_ADMIN,
            UserRole.FACILITY_ADMIN,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only document uploader or admin can delete documents",
            )

        try:
            # Delete file from disk
            if os.path.exists(document.file_path):
                os.remove(document.file_path)

            # Delete database record
            self.db.delete(document)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {str(e)}",
            )

    def update_document_metadata(
        self, document_id: int, extracted_text: str, ai_processed: bool = True
    ) -> ReferralDocument:
        """
        Update document with extracted text and AI processing status.

        Args:
            document_id: Document ID
            extracted_text: Extracted text content
            ai_processed: Whether AI processing is complete

        Returns:
            Updated document object
        """
        document = self.get_document_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        document.extracted_text = extracted_text
        document.ai_processed = ai_processed
        self.db.commit()
        self.db.refresh(document)

        return document

    def get_document_summary(self, document_id: int) -> Dict[str, Any]:
        """
        Get comprehensive document summary.

        Args:
            document_id: Document ID

        Returns:
            Dictionary with document summary
        """
        document = self.get_document_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Get uploader info
        from app.models.user import User

        uploader = self.db.query(User).filter(User.id == document.uploaded_by).first()

        # Get referral info
        referral = (
            self.db.query(Referral).filter(Referral.id == document.referral_id).first()
        )

        return {
            "document_info": {
                "id": document.id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "created_at": document.created_at,
                "ai_processed": document.ai_processed,
            },
            "content_info": {
                "extracted_text": document.extracted_text,
                "text_length": len(document.extracted_text)
                if document.extracted_text
                else 0,
                "has_text": bool(document.extracted_text),
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

    def search_documents(
        self, facility_id: int, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search documents by content or filename within a facility.

        Args:
            facility_id: Facility ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching documents with summaries
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

        # Search documents
        search_term = f"%{query}%"
        documents = (
            self.db.query(ReferralDocument)
            .filter(
                and_(
                    ReferralDocument.referral_id.in_(referral_ids),
                    or_(
                        ReferralDocument.file_name.ilike(search_term),
                        ReferralDocument.extracted_text.ilike(search_term),
                    ),
                )
            )
            .limit(limit)
            .all()
        )

        results = []
        for doc in documents:
            results.append(
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "file_type": doc.file_type,
                    "created_at": doc.created_at,
                    "referral_id": doc.referral_id,
                    "matched_content": self._get_matched_content(
                        doc.extracted_text, query
                    ),
                }
            )

        return results

    def get_document_stats(self, facility_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get document statistics for a facility.

        Args:
            facility_id: Facility ID
            days: Number of days to analyze

        Returns:
            Dictionary with document statistics
        """
        from datetime import datetime, timedelta

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

        # Document statistics
        total_documents = (
            self.db.query(ReferralDocument)
            .filter(ReferralDocument.referral_id.in_(referral_ids))
            .count()
        )

        # Type breakdown
        type_breakdown = {}
        for doc_type in DocumentType:
            count = (
                self.db.query(ReferralDocument)
                .filter(
                    and_(
                        ReferralDocument.referral_id.in_(referral_ids),
                        ReferralDocument.file_type == doc_type.value,
                    )
                )
                .count()
            )
            type_breakdown[doc_type.value] = count

        # AI processing stats
        processed_docs = (
            self.db.query(ReferralDocument)
            .filter(
                and_(
                    ReferralDocument.referral_id.in_(referral_ids),
                    ReferralDocument.ai_processed == True,
                )
            )
            .count()
        )

        # Storage statistics
        total_size = (
            self.db.query(func.sum(ReferralDocument.file_size))
            .filter(ReferralDocument.referral_id.in_(referral_ids))
            .scalar()
            or 0
        )

        return {
            "period_days": days,
            "total_documents": total_documents,
            "type_breakdown": type_breakdown,
            "ai_processed_count": processed_docs,
            "ai_processing_rate": (processed_docs / max(total_documents, 1)) * 100,
            "total_storage_mb": round(total_size / (1024 * 1024), 2),
            "avg_file_size_kb": round((total_size / max(total_documents, 1)) / 1024, 2),
        }

    async def _trigger_text_extraction(self, document_id: int) -> None:
        """Trigger AI text extraction for document (async)."""
        try:
            document = self.get_document_by_id(document_id)
            if not document:
                return

            # Extract text using Document AI Service
            extracted_text = await self._extract_text_from_file(document)

            if extracted_text:
                # Update document with extracted text
                self.update_document_metadata(document_id, extracted_text, True)

                # Trigger AI analysis for medical content
                self._trigger_medical_analysis(document_id, extracted_text)

        except Exception as e:
            print(f"Text extraction failed for document {document_id}: {str(e)}")

    async def _extract_text_from_file(self, document: ReferralDocument) -> str:
        """Extract text from document file using DocumentAIService."""
        try:
            # Initialize Document AI Service
            doc_ai_service = DocumentAIService()

            # Extract text using the AI service
            extraction_result = await doc_ai_service.extract_text_from_document(
                document.file_path
            )

            # Return the extracted text
            return extraction_result.get("text", "")

        except Exception as e:
            print(f"Text extraction failed: {str(e)}")
            return f"[Text extraction failed: {str(e)}]"

    def _trigger_medical_analysis(self, document_id: int, text: str) -> None:
        """Trigger AI medical analysis of extracted text."""
        try:
            ai_service = AIService(self.db)
            document = self.get_document_by_id(document_id)

            # Get referral context
            referral = (
                self.db.query(Referral)
                .filter(Referral.id == document.referral_id)
                .first()
            )
            if not referral:
                return

            # Build context for AI analysis
            context = {
                "document_type": document.file_type,
                "document_text": text,
                "referral_reason": referral.reason_for_referral,
                "patient_name": "Patient",  # Would get from referral
                "age": "Unknown",  # Would get from referral
                 "gender": "Unknown",  # Would get from referral
            }

            # Fix: Ensure logic is inside try block and asyncio is used correctly
            asyncio.create_task(self._run_async_analysis(document_id, context))

        except Exception as e:
            print(f"Medical analysis failed for document {document_id}: {str(e)}")

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


def get_document_service(db: Session) -> DocumentService:
    """Get document service instance."""
    return DocumentService(db)
