"""
Text Cleaning Utilities for Mediflow System

This module provides utilities for cleaning and processing text from
OCR, transcription, and other sources to prepare for AI analysis.
"""

import re
import string
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

class TextCleaner:
    """Utility class for text cleaning and normalization."""
    
    # Medical terminology dictionaries
    MEDICATION_ABBREVIATIONS = {
        'bid': 'twice daily',
        'tid': 'three times daily',
        'qid': 'four times daily',
        'qhs': 'at bedtime',
        'qod': 'every other day',
        'prn': 'as needed',
        'stat': 'immediately',
        'po': 'by mouth',
        'iv': 'intravenous',
        'im': 'intramuscular',
        'sc': 'subcutaneous',
        'sl': 'sublingual',
        'top': 'topical',
        'ng': 'nasogastric',
        'mg': 'milligrams',
        'mcg': 'micrograms',
        'g': 'grams',
        'ml': 'milliliters',
        'l': 'liters',
        'tab': 'tablet',
        'caps': 'capsule',
        'syrup': 'syrup',
        'susp': 'suspension',
        'sol': 'solution'
    }
    
    COMMON_MEDICAL_TERMS = {
        'htn': 'hypertension',
        'dm': 'diabetes mellitus',
        'cad': 'coronary artery disease',
        'chf': 'congestive heart failure',
        'copd': 'chronic obstructive pulmonary disease',
        'uti': 'urinary tract infection',
        'mi': 'myocardial infarction',
        'cva': 'cerebrovascular accident',
        'tIA': 'transient ischemic attack',
        'bmi': 'body mass index',
        'bp': 'blood pressure',
        'hr': 'heart rate',
        'rr': 'respiratory rate',
        'o2': 'oxygen',
        'ecg': 'electrocardiogram',
        'ekg': 'electrocardiogram',
        'cpr': 'cardiopulmonary resuscitation',
        'cath': 'catheter',
        'ivf': 'intravenous fluids',
        'npo': 'nothing by mouth',
        'sob': 'shortness of breath',
        'doe': 'dyspnea on exertion',
        'pnd': 'paroxysmal nocturnal dyspnea',
        'orthopnea': 'orthopnea',
        'edema': 'edema'
    }
    
    # Common OCR errors and corrections
    OCR_CORRECTIONS = {
        'rn': 'm',  # Common OCR confusion
        'cl': 'd',
        '0': 'o',  # Number to letter confusion
        '1': 'l',
        '5': 's',
        '8': 'b',
        'i': 'l',
        't': 'f',
        'c': 'e',
        'a': 'o',
        'n': 'u'
    }
    
    @staticmethod
    def clean_ocr_text(text: str) -> Dict[str, Any]:
        """
        Clean text from OCR sources.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Dictionary with cleaning results
        """
        if not text:
            return {"cleaned_text": "", "corrections_made": 0, "quality_score": 0}
        
        original_text = text
        corrections_made = 0
        
        # Step 1: Basic text normalization
        text = TextCleaner._normalize_whitespace(text)
        text = TextCleaner._fix_line_breaks(text)
        
        # Step 2: OCR-specific corrections
        text, ocr_corrections = TextCleaner._correct_ocr_errors(text)
        corrections_made += len(ocr_corrections)
        
        # Step 3: Medical terminology expansion
        text, med_corrections = TextCleaner._expand_medical_abbreviations(text)
        corrections_made += len(med_corrections)
        
        # Step 4: Remove artifacts and noise
        text, artifacts_removed = TextCleaner._remove_artifacts(text)
        corrections_made += len(artifacts_removed)
        
        # Step 5: Final formatting
        text = TextCleaner._format_medical_text(text)
        
        # Calculate quality score
        quality_score = TextCleaner._calculate_text_quality(original_text, text)
        
        return {
            "cleaned_text": text,
            "original_length": len(original_text),
            "cleaned_length": len(text),
            "corrections_made": corrections_made,
            "ocr_corrections": ocr_corrections,
            "medical_corrections": med_corrections,
            "artifacts_removed": artifacts_removed,
            "quality_score": quality_score,
            "cleaning_timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def clean_transcript(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Clean speech-to-text transcription.
        
        Args:
            text: Raw transcription text
            context: Optional clinical context
            
        Returns:
            Dictionary with cleaning results
        """
        if not text:
            return {"cleaned_text": "", "corrections_made": 0, "confidence": 0}
        
        original_text = text
        corrections_made = 0
        
        # Step 1: Remove conversational fillers
        text, fillers_removed = TextCleaner._remove_fillers(text)
        corrections_made += len(fillers_removed)
        
        # Step 2: Fix common transcription errors
        text, transcription_fixes = TextCleaner._fix_transcription_errors(text)
        corrections_made += len(transcription_fixes)
        
        # Step 3: Expand medical abbreviations
        text, med_corrections = TextCleaner._expand_medical_abbreviations(text)
        corrections_made += len(med_corrections)
        
        # Step 4: Apply context-aware corrections
        if context:
            text, context_corrections = TextCleaner._apply_context_corrections(text, context)
            corrections_made += len(context_corrections)
        
        # Step 5: Format as clinical notes
        text = TextCleaner._format_clinical_notes(text)
        
        # Calculate confidence based on corrections
        confidence = max(0, 100 - (corrections_made * 2))  # Simple confidence calculation
        
        return {
            "cleaned_text": text,
            "original_length": len(original_text),
            "cleaned_length": len(text),
            "corrections_made": corrections_made,
            "fillers_removed": fillers_removed,
            "transcription_fixes": transcription_fixes,
            "medical_corrections": med_corrections,
            "confidence": confidence,
            "cleaning_timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def extract_medical_entities(text: str) -> Dict[str, List[str]]:
        """
        Extract medical entities from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with extracted entities
        """
        entities = {
            "medications": [],
            "dosages": [],
            "vitals": [],
            "symptoms": [],
            "diagnoses": [],
            "procedures": [],
            "lab_values": []
        }
        
        # Medication patterns
        med_patterns = [
            r'\b(\w+)\s+(?:\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|tablet|capsule|syrup))\b',
            r'\b(\w+)\s+(?:\d+\s*(?:mg|mcg|g|ml|tablet|capsule|syrup))\b',
            r'\b(\w+)\s+(?:once|twice|three|four)\s+(?:daily|day)\b'
        ]
        
        for pattern in med_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["medications"].extend(matches)
        
        # Vital signs patterns
        vital_patterns = [
            r'(?:bp|blood pressure)\s*[:/]?\s*(\d{2,3})[/\s](\d{2,3})\s*(?:mmhg)?',
            r'(?:hr|heart rate)\s*[:/]?\s*(\d{2,3})\s*(?:bpm)?',
            r'(?:temp|temperature)\s*[:/]?\s*(\d{2,3}\.?\d*)\s*[°f°FcC]',
            r'(?:o2|oxygen|spo2)\s*[:/]?\s*(\d{2,3})\s*%?',
            r'(?:rr|respiratory rate)\s*[:/]?\s*(\d{1,2})\s*(?:breaths/min)?'
        ]
        
        for pattern in vital_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["vitals"].extend([str(match) for match in matches])
        
        # Lab value patterns
        lab_patterns = [
            r'(\w+)\s*[:/]?\s*(\d+\.?\d*)\s*(?:mg/dl|mmol/l|units/l|pg/ml)',
            r'(?:troponin|ck-mb|bnp|creatinine|glucose)\s*[:/]?\s*(\d+\.?\d*)',
            r'(?:wbc|rbc|hgb|hct|platelets)\s*[:/]?\s*(\d+\.?\d*)'
        ]
        
        for pattern in lab_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["lab_values"].extend([str(match) for match in matches])
        
        # Remove duplicates and clean up
        for key in entities:
            entities[key] = list(set(entities[key]))
            entities[key] = [item.strip() for item in entities[key] if item.strip()]
        
        return entities
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    @staticmethod
    def _fix_line_breaks(text: str) -> str:
        """Fix inappropriate line breaks."""
        # Remove line breaks in the middle of sentences
        text = re.sub(r'([a-z])\n([a-z])', r'\1 \2', text)
        # Fix hyphenated words at line breaks
        text = re.sub(r'([a-z])-\n([a-z])', r'\1\2', text)
        return text
    
    @staticmethod
    def _correct_ocr_errors(text: str) -> Tuple[str, List[str]]:
        """Correct common OCR errors."""
        corrections = []
        
        # Common OCR confusion patterns
        corrections.extend(TextCleaner._apply_corrections(text, TextCleaner.OCR_CORRECTIONS, "OCR correction"))
        
        # Medical term OCR errors
        medical_ocr_errors = {
            'hypertenslon': 'hypertension',
            'diabates': 'diabetes',
            'medicatlon': 'medication',
            'patlent': 'patient',
            'treatment': 'treatment',
            'symptoms': 'symptoms',
            'diagnosis': 'diagnosis'
        }
        
        corrections.extend(TextCleaner._apply_corrections(text, medical_ocr_errors, "Medical OCR correction"))
        
        return text, corrections
    
    @staticmethod
    def _expand_medical_abbreviations(text: str) -> Tuple[str, List[str]]:
        """Expand medical abbreviations."""
        corrections = []
        
        # Case-insensitive abbreviation expansion
        for abbrev, expansion in TextCleaner.MEDICATION_ABBREVIATIONS.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
                corrections.append(f"{abbrev} → {expansion}")
        
        for abbrev, expansion in TextCleaner.COMMON_MEDICAL_TERMS.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
                corrections.append(f"{abbrev} → {expansion}")
        
        return text, corrections
    
    @staticmethod
    def _remove_artifacts(text: str) -> Tuple[str, List[str]]:
        """Remove OCR and processing artifacts."""
        artifacts = []
        
        # Remove page numbers and headers
        if re.search(r'\bpage\s+\d+\b', text, re.IGNORECASE):
            text = re.sub(r'\bpage\s+\d+\b', '', text, flags=re.IGNORECASE)
            artifacts.append("Page numbers")
        
        # Remove common OCR artifacts
        artifact_patterns = [
            r'\[.*?\]',  # Text in brackets
            r'\*\*\*.*?\*\*\*',  # Asterisk-wrapped text
            r'^\d+\s*$',  # Standalone numbers
            r'^[A-Z]+\s*$',  # Standalone uppercase words
            r'^\s*$',  # Empty lines
        ]
        
        for pattern in artifact_patterns:
            if re.search(pattern, text, re.MULTILINE):
                text = re.sub(pattern, '', text, flags=re.MULTILINE)
                artifacts.append(f"Pattern: {pattern}")
        
        return text, artifacts
    
    @staticmethod
    def _format_medical_text(text: str) -> str:
        """Format text for medical documentation."""
        # Ensure proper spacing around medical terms
        text = re.sub(r'(\w)(:)', r'\1 \2', text)
        text = re.sub(r'(:)(\w)', r'\1 \2', text)
        
        # Format measurements properly
        text = re.sub(r'(\d+)\s*(mmhg|bpm|%|°f|°c)', r'\1\2', text, flags=re.IGNORECASE)
        
        # Format time expressions
        text = re.sub(r'(\d+)\s*(am|pm)', r'\1 \2', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def _remove_fillers(text: str) -> List[str]:
        """Remove conversational fillers from transcription."""
        fillers = [
            'um', 'uh', 'er', 'ah', 'like', 'you know', 'you see',
            'basically', 'actually', 'literally', 'sort of', 'kind of',
            'I mean', 'you know what I mean', 'right', 'okay', 'well'
        ]
        
        removed = []
        for filler in fillers:
            pattern = r'\b' + re.escape(filler) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                removed.append(filler)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return removed
    
    @staticmethod
    def _fix_transcription_errors(text: str) -> List[str]:
        """Fix common transcription errors."""
        corrections = []
        
        # Common transcription error patterns
        transcription_fixes = {
            'gonna': 'going to',
            'wanna': 'want to',
            'gotta': 'got to',
            'shoulda': 'should have',
            'coulda': 'could have',
            'woulda': 'would have',
            'mighta': 'might have',
            'cause': 'because',
            "'cause": 'because'
        }
        
        corrections.extend(TextCleaner._apply_corrections(text, transcription_fixes, "Transcription correction"))
        
        return corrections
    
    @staticmethod
    def _apply_context_corrections(text: str, context: Dict[str, Any]) -> List[str]:
        """Apply context-aware corrections."""
        corrections = []
        
        # Use context to guide corrections
        patient_name = context.get('patient_name', '')
        referral_reason = context.get('referral_reason', '')
        specialty = context.get('specialty', '')
        
        # Correct patient name if misspelled
        if patient_name and len(patient_name) > 3:
            # Simple fuzzy matching for patient name
            name_variations = TextCleaner._generate_name_variations(patient_name)
            for variation in name_variations:
                if variation.lower() in text.lower():
                    text = re.sub(re.escape(variation), patient_name, text, flags=re.IGNORECASE)
                    corrections.append(f"Name correction: {variation} → {patient_name}")
                    break
        
        return corrections
    
    @staticmethod
    def _format_clinical_notes(text: str) -> str:
        """Format text as clinical notes."""
        # Add proper punctuation
        text = re.sub(r'([a-z])([A-Z])', r'\1. \2', text)
        
        # Ensure sentences end with proper punctuation
        text = re.sub(r'([a-z0-9])\s+([A-Z])', r'\1. \2', text)
        
        # Format lists and bullet points
        text = re.sub(r'[-*]\s*', '• ', text)
        
        return text.strip()
    
    @staticmethod
    def _apply_corrections(text: str, corrections: Dict[str, str], correction_type: str) -> List[str]:
        """Apply corrections to text and return list of changes made."""
        applied = []
        
        for wrong, correct in corrections.items():
            pattern = r'\b' + re.escape(wrong) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
                applied.append(f"{wrong} → {correct}")
        
        return applied
    
    @staticmethod
    def _generate_name_variations(name: str) -> List[str]:
        """Generate common misspellings/variations of a name."""
        variations = []
        
        # Remove vowels (common misspelling pattern)
        consonants_only = ''.join([c for c in name if c.lower() not in 'aeiou'])
        if len(consonants_only) >= 3:
            variations.append(consonants_only)
        
        # Common substitutions
        substitutions = {
            'a': 'e',
            'e': 'a',
            'i': 'y',
            'y': 'i',
            'c': 'k',
            'k': 'c',
            's': 'z',
            'z': 's'
        }
        
        for original, sub in substitutions.items():
            if original in name.lower():
                variation = name.lower().replace(original, sub)
                variations.append(variation)
        
        return variations[:5]  # Limit to prevent too many variations
    
    @staticmethod
    def _calculate_text_quality(original: str, cleaned: str) -> float:
        """Calculate text quality score based on improvements."""
        if not original:
            return 0.0
        
        # Base score
        score = 50.0
        
        # Length consistency (not too much lost)
        length_ratio = len(cleaned) / max(len(original), 1)
        if 0.8 <= length_ratio <= 1.2:
            score += 20.0
        elif 0.6 <= length_ratio <= 1.4:
            score += 10.0
        
        # Word count improvement
        original_words = len(original.split())
        cleaned_words = len(cleaned.split())
        if cleaned_words >= original_words * 0.9:
            score += 15.0
        
        # Punctuation and formatting
        if re.search(r'[.!?]$', cleaned.strip()):
            score += 10.0
        
        # Medical terminology presence
        med_terms = list(TextCleaner.MEDICATION_ABBREVIATIONS.keys()) + list(TextCleaner.COMMON_MEDICAL_TERMS.keys())
        med_term_count = sum(1 for term in med_terms if term.lower() in cleaned.lower())
        if med_term_count > 0:
            score += min(5.0, med_term_count * 2.0)
        
        return min(100.0, max(0.0, score))

# Convenience functions
def clean_ocr_text(text: str) -> Dict[str, Any]:
    """Clean OCR text with full analysis."""
    return TextCleaner.clean_ocr_text(text)

def clean_transcript(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Clean speech transcription."""
    return TextCleaner.clean_transcript(text, context)

def extract_medical_entities(text: str) -> Dict[str, List[str]]:
    """Extract medical entities from text."""
    return TextCleaner.extract_medical_entities(text)
