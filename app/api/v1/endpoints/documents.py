from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.utils.file_utils import DocumentHandler
from app.utils.audit_utils import create_audit_logger
from app.schemas.document import DocumentResponse, DocumentSummary
from app.models.referral_document import ReferralDocument
from app.models.referral import Referral
from app.models.user import User
from app.enums import UserRole, AuditAction, DocumentType

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    referral_id: int,
    file_type: str = Query(..., description="Type of document (lab_report, discharge_summary, etc.)"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)
    
    # Validate document type
    if file_type not in [dt.value for dt in DocumentType]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {[dt.value for dt in DocumentType]}"
        )
    
    # Verify referral exists
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found"
        )
    
    try:
        # Handle file upload
        document_handler = DocumentHandler()
        file_metadata = await document_handler.handle_upload(file, referral_id, current_user.id)
        
        # Create document record
        document = ReferralDocument(
            referral_id=referral_id,
            uploaded_by=current_user.id,
            file_type=file_type,
            **file_metadata
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Log upload
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPLOAD,
            entity_type="document",
            entity_id=document.id,
            details={
                "referral_id": referral_id,
                "file_name": file.filename,
                "file_type": file_type,
                "file_size": file_metadata["file_size"]
            }
        )
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )

@router.get("/referral/{referral_id}", response_model=List[DocumentSummary])
def list_referral_documents(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents for a referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)
    
    documents = db.query(ReferralDocument).filter(
        ReferralDocument.referral_id == referral_id
    ).order_by(ReferralDocument.created_at.desc()).all()
    
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
            uploader_name=f"{uploader.first_name} {uploader.last_name}" if uploader else "Unknown"
        )
        result.append(summary)
    
    return result

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document by ID."""
    document = db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check referral access
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(document.referral_id)
    
    return document

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document."""
    document = db.query(ReferralDocument).filter(ReferralDocument.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check permissions - only uploader or admin can delete
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(document.referral_id)
    
    if (document.uploaded_by != current_user.id and 
        current_user.role not in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only document uploader or admin can delete documents"
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
            action=AuditAction.DELETE,
            entity_type="document",
            entity_id=document.id,
            details={
                "file_name": document.file_name,
                "referral_id": document.referral_id
            }
        )
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )
