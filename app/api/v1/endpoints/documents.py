from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.services.document_service import get_document_service
from app.utils.audit_utils import create_audit_logger
from app.schemas.document import DocumentResponse, DocumentSummary
from app.models.referral_document import ReferralDocument
from app.models.referral import Referral
from app.models.user import User
from app.enums import UserRole, AuditAction, DocumentType

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    referral_id: int,
    file_type: str = Query(
        ..., description="Type of document (lab_report, discharge_summary, etc.)"
    ),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    # Validate document type
    if file_type not in [dt.value for dt in DocumentType]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {[dt.value for dt in DocumentType]}",
        )

    # Verify referral exists
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    try:
        service = get_document_service(db)
        document = await service.upload_document(
            referral_id=referral_id,
            file=file,
            file_type=file_type,
            uploader_id=current_user.id
        )

        # Log upload
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPLOAD.value,
            entity_type="document",
            entity_id=document.id,
            details={
                "referral_id": referral_id,
                "file_name": file.filename,
                "file_type": file_type,
                "file_size": document.file_size,
            },
        )

        return document

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}",
        )


@router.get("/referral/{referral_id}", response_model=List[DocumentSummary])
def list_referral_documents(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    documents = (
        db.query(ReferralDocument)
        .filter(ReferralDocument.referral_id == referral_id)
        .order_by(ReferralDocument.created_at.desc())
        .all()
    )

    # Create summaries with uploader names
    result = []
    for doc in documents:
        uploader = db.query(User).filter(User.id == doc.uploaded_by).first()
        summary = DocumentSummary(
            id=doc.id,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            created_at=doc.created_at,
            uploader_name=f"{uploader.first_name} {uploader.last_name}"
            if uploader
            else "Unknown",
        )
        result.append(summary)

    return result


@router.get("/facility", response_model=List[DocumentSummary])
def list_facility_documents(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List all documents for the user's facility."""
    # Super Admin can see all documents, others see facility-specific
    if current_user.role == UserRole.SUPER_ADMIN:
        documents = (
            db.query(ReferralDocument)
            .order_by(ReferralDocument.created_at.desc())
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

        # Get all documents for these referrals
        documents = (
            db.query(ReferralDocument)
            .filter(ReferralDocument.referral_id.in_(referral_ids))
            .order_by(ReferralDocument.created_at.desc())
            .all()
        )

    # Create summaries with uploader names
    result = []
    for doc in documents:
        uploader = db.query(User).filter(User.id == doc.uploaded_by).first()
        summary = DocumentSummary(
            id=doc.id,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            created_at=doc.created_at,
            uploader_name=f"{uploader.first_name} {uploader.last_name}"
            if uploader
            else "Unknown",
        )
        result.append(summary)

    return result


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document by ID."""
    document = (
        db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(document.referral_id)

    return document


@router.post("/{document_id}/transcribe")
async def transcribe_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract text from a document using OCR."""
    document = (
        db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(document.referral_id)

    try:
        from app.services.document_ai_service import document_ai_service

        # Extract text from document
        extraction_result = await document_ai_service.extract_text_from_document(
            document.file_path
        )

        # Update document with extracted text
        document.extracted_text = extraction_result.get("text", "")
        document.ai_processed = True
        db.commit()
        db.refresh(document)

        # Log transcription
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE.value,
            entity_type="document",
            entity_id=document.id,
            details={
                "action": "transcribe",
                "extraction_method": extraction_result.get("extraction_method"),
                "text_length": extraction_result.get("text_length", 0),
            },
        )

        return {
            "document_id": document.id,
            "extracted_text": document.extracted_text,
            "extraction_method": extraction_result.get("extraction_method"),
            "confidence": extraction_result.get("confidence"),
            "text_length": len(document.extracted_text),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe document: {str(e)}",
        )


@router.post("/{document_id}/summarize")
async def summarize_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI summary for a document."""
    document = (
        db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(document.referral_id)

    if not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be transcribed before summarization",
        )

    try:
        from app.services.ai_service import AIService
        from app.models.referral import Referral
        from app.models.patient import Patient

        # Get referral and patient context
        referral = (
            db.query(Referral).filter(Referral.id == document.referral_id).first()
        )
        patient = (
            db.query(Patient).filter(Patient.id == referral.patient_id).first()
            if referral
            else None
        )

        ai_service = AIService(db)

        # Build context for AI
        context = {
            "document_type": document.file_type,
            "document_text": document.extracted_text,
            "patient_name": f"{patient.first_name} {patient.last_name}"
            if patient
            else "Unknown",
            "referral_reason": referral.reason_for_referral if referral else "Unknown",
        }

        # Extract document information
        summary_result = await ai_service.extract_document_info(context)

        # Store AI summary in a new field or return it
        # Note: ReferralDocument doesn't have an ai_summary field, so we return it
        return {
            "document_id": document.id,
            "ai_summary": summary_result,
            "document_type": document.file_type,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize document: {str(e)}",
        )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document."""
    document = (
        db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check permissions - only uploader or admin can delete
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(document.referral_id)

    if document.uploaded_by != current_user.id and current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only document uploader or admin can delete documents",
        )

    try:
        # Delete file from disk
        from app.utils.file_utils import FileUtils

        FileUtils.delete_file(document.file_path)

        # Delete database record
        db.delete(document)
        db.commit()

        # Log deletion
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.DELETE.value,
            entity_type="document",
            entity_id=document.id,
            details={
                "file_name": document.file_name,
                "referral_id": document.referral_id,
            },
        )

        return {"message": "Document deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )

@router.get("/documents/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Return file response (adjust path logic as per your storage)
    return FileResponse(doc.file_path, filename=doc.file_name)