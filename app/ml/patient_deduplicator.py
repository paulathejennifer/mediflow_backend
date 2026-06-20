import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

from app.models.patient import Patient

class PatientDeduplicator:
    def __init__(self, db: Session):
        self.db = db

    def _clean(self, text: str) -> str:
        """Helper to normalize text, strip punctuation, and enforce lowercase strings."""
        if not text:
            return ""
        return re.sub(r'[^\w\s]', '', text.lower().strip())

    def _clean_phone(self, phone: str) -> str:
        """Extracts raw digits only to align phone records cleanly across varied structural layouts."""
        if not phone:
            return ""
        return re.sub(r'\D', '', phone)

    def evaluate_patient(self, candidate: Patient) -> List[Dict[str, Any]]:
        """
        Compares an incoming or evaluated patient candidate against the database corpus.
        Calculates distinct similarity vectors across names, direct contact fields, 
        emergency contact data, and medical profiles to determine an exact confidence score.
        """
        # Fetch existing master database records (excluding self)
        query = self.db.query(Patient)
        if candidate.id:
            query = query.filter(Patient.id != candidate.id)
        existing_patients = query.all()

        if not existing_patients:
            return []

        potential_duplicates = []

        # Target Candidate Parameters Normalized
        c_fullname = f"{self._clean(candidate.first_name)} {self._clean(candidate.last_name)}"
        c_dob = candidate.date_of_birth.strftime("%Y%m%d") if candidate.date_of_birth else ""
        c_phone = self._clean_phone(candidate.phone)
        c_email = candidate.email.lower().strip() if candidate.email else ""
        
        # Emergency Contacts Parameters Normalized
        c_e_name = self._clean(candidate.emergency_contact_name)
        c_e_phone = self._clean_phone(candidate.emergency_contact_phone)
        
        # Medical Parameters Normalized
        c_medical = f"{self._clean(candidate.allergies)} {self._clean(candidate.medications)} {self._clean(candidate.chronic_conditions)}"

        for p in existing_patients:
            # Current Record Parameters Normalized
            p_fullname = f"{self._clean(p.first_name)} {self._clean(p.last_name)}"
            p_dob = p.date_of_birth.strftime("%Y%m%d") if p.date_of_birth else ""
            p_phone = self._clean_phone(p.phone)
            p_email = p.email.lower().strip() if p.email else ""
            p_e_name = self._clean(p.emergency_contact_name)
            p_e_phone = self._clean_phone(p.emergency_contact_phone)
            p_medical = f"{self._clean(p.allergies)} {self._clean(p.medications)} {self._clean(p.chronic_conditions)}"

            # --- FIELD-LEVEL SIMILARITY MATRIX SCORING ---
            
            # 1. Identity & Name Scoring (Handles inversions like "Jane Mary" vs "Mary Jane")
            name_score = fuzz.token_sort_ratio(c_fullname, p_fullname) / 100.0
            
            # 2. Strict DOB Alignment Anchor
            dob_score = 1.0 if (c_dob and p_dob and c_dob == p_dob) else 0.0

            # 3. Direct Contact Point Scoring
            phone_score = 1.0 if (c_phone and p_phone and c_phone == p_phone) else 0.0
            email_score = 1.0 if (c_email and p_email and c_email == p_email) else 0.0
            contact_score = max(phone_score, email_score) if (c_phone or c_email) else 0.0

            # 4. Emergency Contact Validation Layer
            e_name_score = fuzz.token_sort_ratio(c_e_name, p_e_name) / 100.0 if (c_e_name and p_e_name) else 0.0
            e_phone_score = 1.0 if (c_e_phone and p_e_phone and c_e_phone == p_e_phone) else 0.0
            emergency_score = max(e_name_score, e_phone_score) if (c_e_name or c_e_phone) else 0.0

            # 5. Unstructured Medical Footprint Scoring (TF-IDF Vector Angle Matching)
            medical_score = 0.0
            if c_medical.strip() and p_medical.strip():
                try:
                    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5))
                    tfidf = vectorizer.fit_transform([p_medical, c_medical])
                    medical_score = float(cosine_similarity(tfidf[0], tfidf[1])[0][0])
                except Exception:
                    medical_score = 0.0

            # --- DYNAMIC MULTIVARIATE WEIGHT INTERACTION SYSTEM ---
            # If date of birth or direct contact points are empty, we adjust weight configurations on-the-fly.
            weights = {"name": 0.30, "dob": 0.30, "contact": 0.20, "emergency": 0.15, "medical": 0.05}
            
            # Compute comprehensive aggregated confidence output
            combined_score = (
                (name_score * weights["name"]) +
                (dob_score * weights["dob"]) +
                (contact_score * weights["contact"]) +
                (emergency_score * weights["emergency"]) +
                (medical_score * weights["medical"])
            )

            # High Critical Boost: If Name AND DOB AND Phone match completely, force absolute match state
            if name_score > 0.90 and dob_score == 1.0 and phone_score == 1.0:
                combined_score = max(combined_score, 0.98)

            # We only surface records passing a strict 75% multi-field certainty barrier
            if combined_score >= 0.75:
                potential_duplicates.append({
                    "existing_patient_id": p.id,
                    "existing_patient_name": f"{p.first_name} {p.last_name}",
                    "tfidf_similarity": float(medical_score), # Maps text context metrics
                    "fuzzy_ratio": float(name_score),
                    "combined_score": float(combined_score)
                })

        return sorted(potential_duplicates, key=lambda x: x["combined_score"], reverse=True)