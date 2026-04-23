"""
AI Service for Mediflow System

This service handles all AI-related operations including:
- Referral summarization (Groq Llama 3.1 8B)
- Speech-to-text transcription (Whisper Large-v3)
- Document OCR and extraction (Tesseract + PDF libraries)
- Risk assessment and missing information identification

The service integrates multiple AI models for optimal performance
and contextualizes outputs using structured prompts.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.utils.ai_prompts import (
    build_referral_summary_prompt,
    build_transcription_cleanup_prompt,
    build_document_extraction_prompt,
    build_missing_info_prompt,
    build_risk_flag_prompt,
    build_ai_disclaimer_prompt
)
from app.core.config import settings
from app.services.text_ai_service import text_ai_service
from app.services.speech_ai_service import speech_ai_service
from app.services.document_ai_service import document_ai_service

class AIService:
    """Service for AI-powered clinical operations using multiple AI models."""
    
    def __init__(self, db: Session):
        self.db = db
        # Initialize AI services
        self.text_ai = text_ai_service
        self.speech_ai = speech_ai_service
        self.document_ai = document_ai_service
        
    async def generate_referral_summary(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate AI-powered referral summary using Groq Llama 3.1.
        
        Args:
            context: Dictionary containing patient and referral information
            
        Returns:
            Dictionary with structured summary components
        """
        try:
            prompt = build_referral_summary_prompt(context)
            
            # Use Groq Llama 3.1 for text summarization
            response = await self.text_ai.generate_referral_summary(prompt)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to generate referral summary: {str(e)}")
    
    async def clean_transcription(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Clean and format voice-to-text transcription using Groq Llama 3.1.
        
        Args:
            context: Dictionary containing raw transcript and clinical context
            
        Returns:
            Dictionary with cleaned transcription and metadata
        """
        try:
            prompt = build_transcription_cleanup_prompt(context)
            
            # Use Groq Llama 3.1 for text cleanup
            response = await self.text_ai.clean_transcription(prompt)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to clean transcription: {str(e)}")
    
    async def extract_document_info(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract key information from medical documents using Groq Llama 3.1.
        
        Args:
            context: Dictionary containing document text and metadata
            
        Returns:
            Dictionary with extracted clinical information
        """
        try:
            prompt = build_document_extraction_prompt(context)
            
            # Use Groq Llama 3.1 for document analysis
            response = await self.text_ai.extract_document_info(prompt)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to extract document information: {str(e)}")
    
    async def identify_missing_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify missing critical information in referrals using Groq Llama 3.1.
        
        Args:
            context: Dictionary containing referral information
            
        Returns:
            Dictionary with missing information assessment
        """
        try:
            prompt = build_missing_info_prompt(context)
            
            # Use Groq Llama 3.1 for missing info analysis
            response = await self.text_ai.identify_missing_info(prompt)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to identify missing information: {str(e)}")
    
    async def assess_risks(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Assess clinical risks in referrals using Groq Llama 3.1.
        
        Args:
            context: Dictionary containing patient and clinical information
            
        Returns:
            Dictionary with risk assessment results
        """
        try:
            prompt = build_risk_flag_prompt(context)
            
            # Use Groq Llama 3.1 for risk assessment
            response = await self.text_ai.assess_risks(prompt)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to assess risks: {str(e)}")
    
    async def transcribe_audio(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper Large-v3.
        
        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en')
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Use Whisper for speech-to-text
            response = await self.speech_ai.transcribe_audio(audio_path, language)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    async def extract_text_from_document(self, file_path: str, document_type: str = "auto") -> Dict[str, Any]:
        """
        Extract text from document using OCR and PDF processing.
        
        Args:
            file_path: Path to document file
            document_type: Type of document ('pdf', 'image', 'auto')
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Use document AI service for OCR and text extraction
            response = await self.document_ai.extract_text_from_document(file_path, document_type)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to extract text from document: {str(e)}")
    
    async def extract_structured_document_data(self, file_path: str, document_type: str = "auto") -> Dict[str, Any]:
        """
        Extract structured medical data from document.
        
        Args:
            file_path: Path to document file
            document_type: Type of document
            
        Returns:
            Dictionary with structured medical information
        """
        try:
            # Use document AI service for structured extraction
            response = await self.document_ai.extract_structured_data(file_path, document_type)
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to extract structured document data: {str(e)}")
    
    def _parse_structured_response(self, response: str) -> Dict[str, str]:
        """
        Parse structured AI response into dictionary.
        
        Args:
            response: AI model response text
            
        Returns:
            Dictionary with parsed sections
        """
        sections = {}
        current_section = None
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line and line.isupper():
                # New section
                current_section = line
                sections[current_section] = ""
            elif current_section and line:
                # Add content to current section
                if sections[current_section]:
                    sections[current_section] += "\n" + line
                else:
                    sections[current_section] = line
        
        return sections
    
    def _get_mock_response(self, prompt: str) -> str:
        """Generate mock response based on prompt content."""
        if "SUMMARY:" in prompt:
            return self._get_mock_referral_summary()
        elif "CLEANED TRANSCRIPTION:" in prompt:
            return self._get_mock_transcription_cleanup()
        else:
            return "Mock AI response - Implement actual API integration"
    
    def _get_mock_referral_summary(self) -> str:
        """Mock referral summary response."""
        return """
SUMMARY:
45-year-old male presenting with chest pain and shortness of breath, referred for cardiac evaluation. ECG shows possible abnormal rhythm.

KEY CLINICAL FINDINGS:
• Chest pain described as pressure-like, 2/10 severity
• Shortness of breath on minimal exertion
• ECG indicates sinus arrhythmia
• History of hypertension controlled with medication

KEY RISKS:
• Potential cardiac instability requiring urgent evaluation
• Hypertension as underlying risk factor
• Possible progression to acute cardiac event

MISSING CRITICAL INFORMATION:
• Current vital signs (BP, heart rate, oxygen saturation)
• Cardiac enzymes (troponin, CK-MB)
• Previous ECG comparisons
• Current medication adherence

RECOMMENDED NEXT STEPS:
• Urgent cardiac evaluation within 24 hours
• Complete cardiac workup including enzymes and imaging
• Blood pressure optimization
• Consider stress testing based on evaluation

UNCERTAINTY LEVEL:
Medium - Limited vital signs and diagnostic data

MEDICAL SAFETY NOTE:
This AI-generated summary is for informational purposes only and does not replace clinical judgment. Receiving clinicians should review all source documents and perform their own assessment.
"""
    
    def _get_mock_transcription_cleanup(self) -> str:
        """Mock transcription cleanup response."""
        return """
CLEANED TRANSCRIPTION:
Patient is a 45-year-old male presenting to emergency department with chest pain. Pain described as pressure-like, central chest, radiating to left arm. Started 2 hours ago. Associated with shortness of breath and diaphoresis. Pain is 8/10 severity.

Past medical history significant for hypertension diagnosed 3 years ago. Medications include amlodipine 5mg daily. Patient reports medication adherence is inconsistent.

Vital signs on presentation: BP 160/95, HR 110, RR 20, SpO2 94% on room air.

TERMINOLOGY CORRECTIONS:
• "amlodipine" corrected from "amlopodine"
• "diaphoresis" corrected from "sweating a lot"
• "SpO2" added for oxygen saturation

CONFIDENCE LEVEL:
High - Clear audio quality with minimal background noise

NOTES:
Some medication dosage information unclear - recommend verification with patient.
"""
    
    def _get_mock_document_extraction(self) -> str:
        """Mock document extraction response."""
        return """
DOCUMENT SUMMARY:
ECG report showing sinus rhythm with frequent premature ventricular contractions. No acute ST-segment changes noted.

KEY FINDINGS:
• Heart rate: 95 bpm (sinus rhythm)
• PVCs: Approximately 8-10 per minute
• PR interval: 160 ms (normal)
• QRS duration: 100 ms (normal)
• QT interval: 420 ms (normal)
• No ST elevation or depression
• T waves normal in morphology

ABNORMAL RESULTS:
• Frequent premature ventricular contractions
• Slightly elevated heart rate

RECOMMENDATIONS:
• Cardiology consultation recommended
• Consider Holter monitoring for rhythm assessment
• Review medication effects on cardiac rhythm
• Follow-up ECG in 1-2 weeks

URGENCY LEVEL:
Medium - Non-acute but requires cardiology evaluation

EXTRACTION CONFIDENCE:
High - Clear, complete ECG report with standard measurements
"""
    
    def _get_mock_missing_info(self) -> str:
        """Mock missing information assessment."""
        return """
MISSING CRITICAL INFO:
• Current vital signs and hemodynamic status
• Cardiac enzyme levels (troponin, CK-MB)
• Complete medication list and adherence
• Allergy status documentation
• Previous cardiac history and interventions

MISSING IMPORTANT INFO:
• Family history of cardiac disease
• Social history (smoking, alcohol use)
• Recent activity level and functional status
• Previous response to cardiac medications

COMPLETENESS SCORE:
60% - Basic information present but critical diagnostic data missing

SAFETY RISK LEVEL:
High - Missing vital signs and cardiac enzymes for chest pain presentation

RECOMMENDED ACTIONS:
• Obtain vital signs immediately
• Order cardiac enzyme panel
• Complete medication reconciliation
• Document allergy status
• Obtain previous medical records

URGENCY OF COMPLETION:
Immediate - Critical information missing for appropriate triage and treatment
"""
    
    def _get_mock_risk_assessment(self) -> str:
        """Mock risk assessment response."""
        return """
IMMEDIATE SAFETY CONCERNS:
• Chest pain with shortness of breath - possible acute coronary syndrome
• Hypertension with poor medication adherence
• Frequent PVCs on ECG

POTENTIAL COMPLICATIONS:
• Progression to myocardial infarction
• Arrhythmia development
• Hypertensive crisis
• Cardiac decompensation

CRITICAL ALERTS:
• Requires immediate cardiac evaluation
• Missing critical diagnostic data
• Medication non-adherence risk

MONITORING RECOMMENDATIONS:
• Continuous cardiac monitoring
• Serial vital signs every 15 minutes
• Cardiac enzyme monitoring
• Blood pressure monitoring

COMMUNICATION NEEDS:
• Urgent notification to cardiology service
• Update to referring facility on patient status
• Family notification if condition worsens

OVERALL RISK LEVEL:
High - Acute cardiac symptoms with significant risk factors

RECOMMENDED ACTIONS:
• Immediate emergency department evaluation
• Cardiology consultation within 1 hour
• Complete cardiac workup
• Blood pressure optimization
• Consider admission for observation
"""

    def get_ai_service_info(self) -> Dict[str, Any]:
        """Get comprehensive information about all AI services."""
        return {
            "text_ai": self.text_ai.get_model_info(),
            "speech_ai": self.speech_ai.get_model_info(),
            "document_ai": self.document_ai.get_service_info(),
            "integration_status": {
                "groq_configured": self.text_ai.client is not None,
                "whisper_loaded": self.speech_ai.model is not None,
                "tesseract_available": self.document_ai.tesseract_available
            },
            "capabilities": {
                "text_summarization": "Groq Llama 3.1 8B",
                "speech_to_text": "Whisper Large-v3",
                "document_ocr": "Tesseract + PDF libraries",
                "medical_entity_extraction": "Integrated with text processing",
                "risk_assessment": "Groq Llama 3.1 8B",
                "missing_info_detection": "Groq Llama 3.1 8B"
            },
            "api_endpoints": [
                "/ai/test-summary",
                "/ai/test-transcription", 
                "/ai/test-document-extraction",
                "/ai/referral/{id}/summarize",
                "/ai/status",
                "/ai/health"
            ]
        }

def get_ai_service(db: Session) -> AIService:
    """Get AI service instance."""
    return AIService(db)
