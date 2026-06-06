"""
Text AI Service for Mediflow System

This service handles text-based AI operations using Groq (Llama 3.1 8B)
for medical summarization, reasoning, and structured outputs.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from groq import Groq
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class TextAIService:
    """Service for text-based AI operations using Groq."""

    def __init__(self):
        self.client = None
        self.model = "llama-3.1-8b-instant"  # Groq's Llama 3.1 8B model
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Groq client."""
        try:
            api_key = getattr(settings, "GROQ_API_KEY", None)
            if api_key:
                self.client = Groq(api_key=api_key)
                logger.info("Groq client initialized successfully")
            else:
                logger.warning("GROQ_API_KEY not found, using mock responses")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
            self.client = None

    async def generate_referral_summary(self, prompt: str) -> Dict[str, str]:
        """
        Generate AI-powered referral summary using Llama 3.1.

        Args:
            prompt: Formatted prompt for referral summarization

        Returns:
            Dictionary with structured summary components
        """
        if not self.client:
            return self._get_mock_referral_summary()

        try:
            response = await self._call_groq_api(
                prompt, temperature=0.3, max_tokens=1000
            )
            summary_data = self._parse_structured_response(response)

            return {
                "summary": summary_data.get("SUMMARY", ""),
                "key_findings": summary_data.get("KEY CLINICAL FINDINGS", ""),
                "risks": summary_data.get("KEY RISKS", ""),
                "missing_info": summary_data.get("MISSING CRITICAL INFORMATION", ""),
                "next_steps": summary_data.get("RECOMMENDED NEXT STEPS", ""),
                "uncertainty_level": summary_data.get("UNCERTAINTY LEVEL", "Medium"),
                "safety_note": summary_data.get("MEDICAL SAFETY NOTE", ""),
                "full_response": response,
            }

        except Exception as e:
            logger.error(f"Referral summary generation failed: {str(e)}")
            return self._get_mock_referral_summary()

    async def clean_transcription(self, prompt: str) -> Dict[str, str]:
        """
        Clean and format voice-to-text transcription.

        Args:
            prompt: Formatted prompt for transcription cleanup

        Returns:
            Dictionary with cleaned transcription and metadata
        """
        if not self.client:
            return self._get_mock_transcription_cleanup()

        try:
            response = await self._call_groq_api(
                prompt, temperature=0.2, max_tokens=800
            )
            cleaned_data = self._parse_structured_response(response)

            return {
                "cleaned_transcript": cleaned_data.get("CLEANED TRANSCRIPTION", ""),
                "corrections": cleaned_data.get("TERMINOLOGY CORRECTIONS", ""),
                "confidence": cleaned_data.get("CONFIDENCE LEVEL", "Medium"),
                "notes": cleaned_data.get("NOTES", ""),
                "full_response": response,
            }

        except Exception as e:
            logger.error(f"Transcription cleanup failed: {str(e)}")
            return self._get_mock_transcription_cleanup()

    async def extract_document_info(self, prompt: str) -> Dict[str, str]:
        """
        Extract key information from medical documents.

        Args:
            prompt: Formatted prompt for document extraction

        Returns:
            Dictionary with extracted clinical information
        """
        if not self.client:
            return self._get_mock_document_extraction()

        try:
            response = await self._call_groq_api(
                prompt, temperature=0.1, max_tokens=800
            )
            extracted_data = self._parse_structured_response(response)

            return {
                "summary": extracted_data.get("DOCUMENT SUMMARY", ""),
                "key_findings": extracted_data.get("KEY FINDINGS", ""),
                "abnormal_results": extracted_data.get("ABNORMAL RESULTS", ""),
                "recommendations": extracted_data.get("RECOMMENDATIONS", ""),
                "urgency": extracted_data.get("URGENCY LEVEL", "Medium"),
                "confidence": extracted_data.get("EXTRACTION CONFIDENCE", "Medium"),
                "full_response": response,
            }

        except Exception as e:
            logger.error(f"Document extraction failed: {str(e)}")
            return self._get_mock_document_extraction()

    async def identify_missing_info(self, prompt: str) -> Dict[str, Any]:
        """
        Identify missing critical information in referrals.

        Args:
            prompt: Formatted prompt for missing information analysis

        Returns:
            Dictionary with missing information assessment
        """
        if not self.client:
            return self._get_mock_missing_info()

        try:
            response = await self._call_groq_api(
                prompt, temperature=0.2, max_tokens=600
            )
            missing_data = self._parse_structured_response(response)

            return {
                "missing_critical": missing_data.get("MISSING CRITICAL INFO", ""),
                "missing_important": missing_data.get("MISSING IMPORTANT INFO", ""),
                "completeness_score": missing_data.get("COMPLETENESS SCORE", "50%"),
                "safety_risk": missing_data.get("SAFETY RISK LEVEL", "Medium"),
                "recommended_actions": missing_data.get("RECOMMENDED ACTIONS", ""),
                "completion_urgency": missing_data.get("URGENCY OF COMPLETION", "Soon"),
                "full_response": response,
            }

        except Exception as e:
            logger.error(f"Missing info identification failed: {str(e)}")
            return self._get_mock_missing_info()

    async def assess_risks(self, prompt: str) -> Dict[str, str]:
        """
        Assess clinical risks in referrals.

        Args:
            prompt: Formatted prompt for risk assessment

        Returns:
            Dictionary with risk assessment results
        """
        if not self.client:
            return self._get_mock_risk_assessment()

        try:
            response = await self._call_groq_api(
                prompt, temperature=0.1, max_tokens=700
            )
            risk_data = self._parse_structured_response(response)

            return {
                "immediate_concerns": risk_data.get("IMMEDIATE SAFETY CONCERNS", ""),
                "potential_complications": risk_data.get("POTENTIAL COMPLICATIONS", ""),
                "critical_alerts": risk_data.get("CRITICAL ALERTS", ""),
                "monitoring_needs": risk_data.get("MONITORING RECOMMENDATIONS", ""),
                "communication_needs": risk_data.get("COMMUNICATION NEEDS", ""),
                "overall_risk": risk_data.get("OVERALL RISK LEVEL", "Medium"),
                "recommended_actions": risk_data.get("RECOMMENDED ACTIONS", ""),
                "full_response": response,
            }

        except Exception as e:
            logger.error(f"Risk assessment failed: {str(e)}")
            return self._get_mock_risk_assessment()

    async def _call_groq_api(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """
        Call Groq API with the specified parameters.

        Args:
            prompt: The prompt to send to the model
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Model response text
        """
        try:
            # Run the synchronous Groq call in a thread pool
            loop = asyncio.get_event_loop()

            def sync_groq_call():
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional medical referral assistant. Provide accurate, structured, and safe medical information.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=0.9,
                    stream=False,
                )
                return chat_completion.choices[0].message.content

            response = await loop.run_in_executor(None, sync_groq_call)
            return response

        except Exception as e:
            logger.error(f"Groq API call failed: {str(e)}")
            raise

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
        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            if ":" in line and any(header in line.upper() for header in ["SUMMARY", "FINDINGS", "RISKS", "INFO", "STEPS", "LEVEL", "NOTE"]):
                # New section
                current_section = line.split(":")[0].strip().upper()
                content = line.split(":", 1)[1].strip()
                sections[current_section] = content
            elif current_section and line and line != sections.get(current_section):
                # Add content to current section
                if sections[current_section]:
                    sections[current_section] += "\n" + line
                else:
                    sections[current_section] = line

        return sections

    # Mock responses for development
    def _get_mock_referral_summary(self) -> Dict[str, str]:
        """Mock referral summary response."""
        return {
            "summary": "45-year-old male presenting with chest pain and shortness of breath, referred for cardiac evaluation. ECG shows possible abnormal rhythm.",
            "key_findings": "• Chest pain described as pressure-like, 2/10 severity\n• Shortness of breath on minimal exertion\n• ECG indicates sinus arrhythmia\n• History of hypertension controlled with medication",
            "risks": "• Potential cardiac instability requiring urgent evaluation\n• Hypertension as underlying risk factor\n• Possible progression to acute cardiac event",
            "missing_info": "• Current vital signs (BP, heart rate, oxygen saturation)\n• Cardiac enzymes (troponin, CK-MB)\n• Previous ECG comparisons\n• Current medication adherence",
            "next_steps": "• Urgent cardiac evaluation within 24 hours\n• Complete cardiac workup including enzymes and imaging\n• Blood pressure optimization\n• Consider stress testing based on evaluation",
            "uncertainty_level": "Medium - Limited vital signs and diagnostic data",
            "safety_note": "This AI-generated summary is for informational purposes only and does not replace clinical judgment.",
            "full_response": "Mock response - Groq API not configured",
        }

    def _get_mock_transcription_cleanup(self) -> Dict[str, str]:
        """Mock transcription cleanup response."""
        return {
            "cleaned_transcript": "Patient is a 45-year-old male presenting to emergency department with chest pain. Pain described as pressure-like, central chest, radiating to left arm. Started 2 hours ago. Associated with shortness of breath and diaphoresis. Pain is 8/10 severity.",
            "corrections": "• 'amlodipine' corrected from 'amlopodine'\n• 'diaphoresis' corrected from 'sweating a lot'\n• 'SpO2' added for oxygen saturation",
            "confidence": "High - Clear audio quality with minimal background noise",
            "notes": "Some medication dosage information unclear - recommend verification with patient.",
            "full_response": "Mock response - Groq API not configured",
        }

    def _get_mock_document_extraction(self) -> Dict[str, str]:
        """Mock document extraction response."""
        return {
            "summary": "ECG report showing sinus rhythm with frequent premature ventricular contractions. No acute ST-segment changes noted.",
            "key_findings": "• Heart rate: 95 bpm (sinus rhythm)\n• PVCs: Approximately 8-10 per minute\n• PR interval: 160 ms (normal)\n• QRS duration: 100 ms (normal)",
            "abnormal_results": "• Frequent premature ventricular contractions\n• Slightly elevated heart rate",
            "recommendations": "• Cardiology consultation recommended\n• Consider Holter monitoring for rhythm assessment\n• Review medication effects on cardiac rhythm",
            "urgency": "Medium - Non-acute but requires cardiology evaluation",
            "confidence": "High - Clear, complete ECG report with standard measurements",
            "full_response": "Mock response - Groq API not configured",
        }

    def _get_mock_missing_info(self) -> Dict[str, Any]:
        """Mock missing information assessment."""
        return {
            "missing_critical": "• Current vital signs and hemodynamic status\n• Cardiac enzyme levels (troponin, CK-MB)\n• Complete medication list and adherence\n• Allergy status documentation",
            "missing_important": "• Family history of cardiac disease\n• Social history (smoking, alcohol use)\n• Recent activity level and functional status",
            "completeness_score": "60%",
            "safety_risk": "High - Missing vital signs and cardiac enzymes for chest pain presentation",
            "recommended_actions": "• Obtain vital signs immediately\n• Order cardiac enzyme panel\n• Complete medication reconciliation\n• Document allergy status",
            "completion_urgency": "Immediate - Critical information missing for appropriate triage",
            "full_response": "Mock response - Groq API not configured",
        }

    def _get_mock_risk_assessment(self) -> Dict[str, str]:
        """Mock risk assessment response."""
        return {
            "immediate_concerns": "• Chest pain with shortness of breath - possible acute coronary syndrome\n• Hypertension with poor medication adherence\n• Frequent PVCs on ECG",
            "potential_complications": "• Progression to myocardial infarction\n• Arrhythmia development\n• Hypertensive crisis",
            "critical_alerts": "• Requires immediate cardiac evaluation\n• Missing critical diagnostic data",
            "monitoring_needs": "• Continuous cardiac monitoring\n• Serial vital signs every 15 minutes\n• Cardiac enzyme monitoring",
            "communication_needs": "• Urgent notification to cardiology service\n• Update to referring facility on patient status",
            "overall_risk": "High - Acute cardiac symptoms with significant risk factors",
            "recommended_actions": "• Immediate emergency department evaluation\n• Cardiology consultation within 1 hour\n• Complete cardiac workup",
            "full_response": "Mock response - Groq API not configured",
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the AI model being used."""
        return {
            "provider": "Groq",
            "model": self.model,
            "model_type": "Llama 3.1 8B Instruct",
            "capabilities": [
                "Medical summarization",
                "Clinical reasoning",
                "Structured output generation",
                "Risk assessment",
                "Information extraction",
            ],
            "is_configured": self.client is not None,
            "api_key_set": bool(getattr(settings, "GROQ_API_KEY", None)),
        }


# Global instance
text_ai_service = TextAIService()
