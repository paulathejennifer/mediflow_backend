from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.ml.patient_deduplicator import PatientDeduplicator
from app.models.duplicate_patient import DuplicatePatientPair

router = APIRouter()

@router.post("/scan/{patient_id}", response_model=List[Dict[str, Any]])
def scan_patient_duplicates(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the Multivariate Machine Learning Engine to scan for duplicates 
    against a specific patient record.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Patient record not found"
        )
        
    # Execute ML Engine scan
    deduplicator = PatientDeduplicator(db)
    potential_duplicates = deduplicator.evaluate_patient(patient)
    
    # Save findings into tracking table
    for match in potential_duplicates:
        existing_log = db.query(DuplicatePatientPair).filter(
            DuplicatePatientPair.new_patient_id == patient_id,
            DuplicatePatientPair.existing_patient_id == match["existing_patient_id"]
        ).first()
        
        if not existing_log:
            new_pair = DuplicatePatientPair(
                new_patient_id=patient_id,
                existing_patient_id=match["existing_patient_id"],
                tfidf_similarity=match["tfidf_similarity"],
                fuzzy_ratio=match["fuzzy_ratio"],
                combined_score=match["combined_score"],
                status="flagged"
            )
            db.add(new_pair)
            
    db.commit()
    return potential_duplicates

@router.get("/flagged", response_model=List[Dict[str, Any]])
def list_flagged_duplicates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all outstanding flagged patient variations currently caught in the system pipeline."""
    pairs = db.query(DuplicatePatientPair).filter(DuplicatePatientPair.status == "flagged").all()
    
    results = []
    for pair in pairs:
        results.append({
            "id": pair.id,
            "new_patient_id": pair.new_patient_id,
            "new_patient_name": f"{pair.new_patient.first_name} {pair.new_patient.last_name}" if pair.new_patient else "Unknown",
            "existing_patient_id": pair.existing_patient_id,
            "existing_patient_name": f"{pair.existing_patient.first_name} {pair.existing_patient.last_name}" if pair.existing_patient else "Unknown",
            "combined_score": pair.combined_score,
            "status": pair.status,
            "created_at": pair.created_at
        })
    return results

@router.post("/resolve/{pair_id}/{action}")
def resolve_duplicate_flag(
    pair_id: int,
    action: str, # 'merge' or 'dismiss'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process administrative audit actions to merge records or clear flags."""
    pair = db.query(DuplicatePatientPair).filter(DuplicatePatientPair.id == pair_id).first()
    if not pair:
        raise HTTPException(status_code=404, detail="Duplicate pair flag reference not found")
        
    if action not in ["merge", "dismiss"]:
        raise HTTPException(status_code=400, detail="Invalid resolution path. Select 'merge' or 'dismiss'")
        
    pair.status = "merged" if action == "merge" else "dismissed"
    db.commit()
    return {"message": f"Patient match flag successfully updated to {pair.status}"}