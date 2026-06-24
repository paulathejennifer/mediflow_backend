import json
import logging
from sqlalchemy.orm import Session
from app.models.referral import Referral
from app.core.config import settings
from groq import Groq

logger = logging.getLogger(__name__)

class ReferralIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        # Falling back to a placeholder string if key is unset so initialization doesn't throw a fatal error
        api_key = getattr(settings, "GROQ_API_KEY", None) or "YOUR_GROQ_API_KEY"
        self.client = Groq(api_key=api_key)

    async def analyze_referral(self, referral_id: int) -> dict:
        """
        Parses referral contents via Groq Llama 3.1 to extract structured JSON metadata:
        Reason Category, Intended Medical Specialty, Urgency Ranking, and Clinical Keywords.
        """
        referral = self.db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            raise ValueError(f"Referral with ID {referral_id} not found.")

        # Combine data inputs safely
        source_text = f"""
        Reason for Referral: {referral.reason_for_referral or ''}
        Clinical Notes: {referral.clinical_notes or ''}
        Initial Priority: {referral.priority or ''}
        """

        prompt = f"""
            You are a highly experienced clinical data analysis assistant. Examine the unstructured clinical referral text provided below.
            Extract specific categorizations to map out systemic routing. You must respond with raw, valid JSON only matching this exact schema:
        {{
            "extracted_reason": "Brief unified categorization of the underlying condition or reason",
            "specialty": "MUST be exactly one of these options: Cardiology, Endocrinology, Neurology, Orthopedics, Oncology, Pediatrics, Obstetrics & Gynecology, General Surgery, Ophthalmology, Dermatology, Psychiatry, Nephrology, Pulmonology, Gastroenterology, Urology, ENT, Hematology, Rheumatology, Infectious Disease, General Medicine",
            "urgency_score": "High", "Medium", or "Low" based on clinical presentation strings,
            "keywords": ["list", "of", "vital", "clinical", "terms", "symptoms", "or", "biopsies"]
        }}
        Rules:
        - The specialty field MUST be copied exactly from the list above, no variations, no abbreviations.
        - If unsure, pick the closest match. If truly unrelated to any specialty, use General Medicine.
        - Do not include any pleasantries, conversational fillers, or markdown codeblocks outside of raw JSON text.

        Clinical Referral Data:
        {source_text}
        """

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            parsed_data = json.loads(result_text)

            # Store the structured analysis onto your referral model (using JSON string mapping)
            # You can store this directly inside your existing 'ai_summary' column or extend via structured dictionary blobs
            analysis_meta = {
                "v2_intelligence": parsed_data,
                "original_summary": referral.ai_summary
            }
            referral.ai_summary = json.dumps(analysis_meta)
            self.db.commit()

            return parsed_data

        except Exception as e:
            logger.error(f"Error executing AI Referral Intelligence loop: {str(e)}")
            # Fail-safe breakdown to prevent blocking application pipelines
            return {
                "extracted_reason": "Failed to parse automatically",
                "specialty": "Review Required",
                "urgency_score": referral.priority or "Medium",
                "keywords": []
            }