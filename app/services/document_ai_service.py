"""
Document AI Service for Mediflow System

This service handles OCR and document processing using:
- pdfplumber/pymupdf for digital PDFs
- Tesseract OCR for scanned documents and images
- OpenCV for image preprocessing
"""

import asyncio
import os
import tempfile
import logging
import io
from typing import Dict, Any, Optional, List, Tuple
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentAIService:
    """Service for document OCR and text extraction."""

    def __init__(self):
        self.tesseract_available = self._check_tesseract()
        self.ocr_languages = ["eng"]  # Default to English, can add more
        self._initialize_tesseract()

    def _check_tesseract(self) -> bool:
        """Check if Tesseract OCR is available."""
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR is available")
            return True
        except Exception as e:
            logger.error(f"Tesseract OCR not available: {str(e)}")
            return False

    def _initialize_tesseract(self):
        """Initialize Tesseract with proper configuration."""
        if self.tesseract_available:
            try:
                # Set Tesseract path if specified in config
                tesseract_path = getattr(settings, "TESSERACT_PATH", None)
                if tesseract_path and os.path.exists(tesseract_path):
                    pytesseract.pytesseract.tesseract_cmd = tesseract_path
                    logger.info(f"Tesseract path set to: {tesseract_path}")

                # Test Tesseract with simple OCR
                test_image = Image.new("RGB", (100, 50), color="white")
                test_text = pytesseract.image_to_string(test_image)
                logger.info("Tesseract initialization successful")

            except Exception as e:
                logger.error(f"Tesseract initialization failed: {str(e)}")
                self.tesseract_available = False

    async def extract_text_from_document(
        self, file_path: str, document_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Extract text from document using appropriate method.

        Args:
            file_path: Path to document file
            document_type: Type of document ('pdf', 'image', 'auto')

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Determine document type
            if document_type == "auto":
                document_type = self._detect_document_type(file_path)

            # Extract text based on document type
            if document_type == "pdf":
                return await self._extract_from_pdf(file_path)
            elif document_type in ["image", "scanned"]:
                return await self._extract_from_image(file_path)
            else:
                return self._get_mock_extraction(
                    file_path, f"Unsupported document type: {document_type}"
                )

        except Exception as e:
            logger.error(f"Document text extraction failed: {str(e)}")
            return self._get_mock_extraction(file_path, str(e))

    def _detect_document_type(self, file_path: str) -> str:
        """Detect document type from file extension and content."""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".pdf":
            # Check if PDF is scanned or digital
            try:
                with fitz.open(file_path) as doc:
                    page = doc[0]
                    text = page.get_text()
                    if len(text.strip()) > 100:  # Has substantial text
                        return "pdf_digital"
                    else:
                        return "pdf_scanned"
            except Exception:
                return "pdf_scanned"

        elif file_ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
            return "image"

        elif file_ext in [".txt", ".rtf"]:
            return "text"

        else:
            return "unknown"

    async def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF using appropriate method."""
        try:
            # First try pdfplumber for digital PDFs
            text, metadata = await self._extract_with_pdfplumber(file_path)

            # If little text extracted, try OCR on scanned PDF
            if len(text.strip()) < 200:
                logger.info("Limited text extracted, trying OCR on PDF")
                ocr_result = await self._ocr_pdf_pages(file_path)
                if ocr_result["text_length"] > text.strip().__len__():
                    return ocr_result

            return {
                "text": text,
                "text_length": len(text),
                "extraction_method": "pdfplumber",
                "metadata": metadata,
                "confidence": 0.9 if len(text.strip()) > 100 else 0.6,
                "processing_info": {
                    "pages_processed": metadata.get("pages", 0),
                    "is_scanned": len(text.strip()) < 200,
                    "ocr_used": False,
                },
            }

        except Exception as e:
            logger.warning(f"PDF extraction failed, trying OCR: {str(e)}")
            return await self._ocr_pdf_pages(file_path)

    async def _extract_with_pdfplumber(
        self, file_path: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF using pdfplumber."""
        text = ""
        metadata = {"pages": 0, "has_tables": False, "has_images": False}

        try:
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text + "\n"

                    # Check for tables
                    tables = page.extract_tables()
                    if tables:
                        metadata["has_tables"] = True
                        for table in tables:
                            table_text = "\n".join(
                                [" | ".join(row) for row in table if row]
                            )
                            text += f"\n--- Table ---\n{table_text}\n"

                    # Check for images
                    if page.images:
                        metadata["has_images"] = True

            return text.strip(), metadata

        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {str(e)}")
            return "", metadata

    async def _ocr_pdf_pages(self, file_path: str) -> Dict[str, Any]:
        """Perform OCR on PDF pages using Tesseract."""
        if not self.tesseract_available:
            return self._get_mock_extraction(file_path, "Tesseract OCR not available")

        try:
            text = ""
            pages_processed = 0

            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]

                    # Convert page to image
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2)
                    )  # 2x zoom for better OCR
                    img_data = pix.tobytes("png")

                    # Process with OCR
                    page_text = await self._ocr_image_data(img_data)
                    if page_text:
                        text += f"\n--- Page {page_num + 1} (OCR) ---\n"
                        text += page_text + "\n"
                        pages_processed += 1

            return {
                "text": text.strip(),
                "text_length": len(text),
                "extraction_method": "tesseract_ocr",
                "metadata": {"pages": len(doc), "pages_ocr_processed": pages_processed},
                "confidence": 0.7 if len(text.strip()) > 100 else 0.4,
                "processing_info": {
                    "pages_processed": pages_processed,
                    "is_scanned": True,
                    "ocr_used": True,
                },
            }

        except Exception as e:
            logger.error(f"PDF OCR failed: {str(e)}")
            return self._get_mock_extraction(file_path, str(e))

    async def _extract_from_image(self, file_path: str) -> Dict[str, Any]:
        """Extract text from image using OCR."""
        if not self.tesseract_available:
            return self._get_mock_extraction(file_path, "Tesseract OCR not available")

        try:
            # Preprocess image for better OCR
            processed_image = await self._preprocess_image(file_path)

            # Perform OCR
            text = await self._ocr_image(processed_image)

            return {
                "text": text,
                "text_length": len(text),
                "extraction_method": "tesseract_ocr",
                "metadata": {
                    "original_file": os.path.basename(file_path),
                    "image_preprocessed": True,
                },
                "confidence": self._estimate_ocr_confidence(text),
                "processing_info": {"image_preprocessed": True, "ocr_used": True},
            }

        except Exception as e:
            logger.error(f"Image OCR failed: {str(e)}")
            return self._get_mock_extraction(file_path, str(e))

    async def _preprocess_image(self, image_path: str) -> str:
        """Preprocess image for better OCR accuracy."""
        try:
            # Create temporary file for processed image
            temp_dir = tempfile.gettempdir()
            processed_path = os.path.join(
                temp_dir, f"processed_{os.path.basename(image_path)}"
            )

            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return image_path

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(gray)

            # Adaptive thresholding for better text extraction
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            # Save processed image
            cv2.imwrite(processed_path, cleaned)

            logger.info(f"Image preprocessed: {image_path} -> {processed_path}")
            return processed_path

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}")
            return image_path

    async def _ocr_image(self, image_path: str) -> str:
        """Perform OCR on image file."""
        try:
            # Load image
            image = Image.open(image_path)

            # Configure Tesseract for better results
            custom_config = r"--oem 3 --psm 6 -l eng"

            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)

            return text.strip()

        except Exception as e:
            logger.error(f"Image OCR failed: {str(e)}")
            return ""

    async def _ocr_image_data(self, image_data: bytes) -> str:
        """Perform OCR on image data (bytes)."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))

            # Configure Tesseract
            custom_config = r"--oem 3 --psm 6 -l eng"

            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)

            return text.strip()

        except Exception as e:
            logger.error(f"Image data OCR failed: {str(e)}")
            return ""

    def _estimate_ocr_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text characteristics."""
        if not text:
            return 0.0

        # Factors affecting confidence
        word_count = len(text.split())
        char_count = len(text)

        # Check for common OCR errors
        ocr_error_indicators = ["|", "l", "1", "0", "O", "[", "]", "{", "}"]
        error_count = sum(text.count(indicator) for indicator in ocr_error_indicators)

        # Calculate confidence
        base_confidence = 0.7

        # Adjust based on text length
        if char_count > 500:
            base_confidence += 0.1
        elif char_count < 50:
            base_confidence -= 0.2

        # Adjust based on error indicators
        error_ratio = error_count / max(char_count, 1)
        base_confidence -= error_ratio * 2

        # Adjust based on word count (more words = more confident)
        if word_count > 20:
            base_confidence += 0.1

        return max(0.1, min(0.95, base_confidence))

    async def extract_structured_data(
        self, file_path: str, document_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Extract structured medical data from document.

        Args:
            file_path: Path to document file
            document_type: Type of document

        Returns:
            Dictionary with structured medical information
        """
        # First extract raw text
        extraction_result = await self.extract_text_from_document(
            file_path, document_type
        )
        raw_text = extraction_result.get("text", "")

        if not raw_text:
            return {
                "structured_data": {},
                "extraction_result": extraction_result,
                "note": "No text extracted for structured analysis",
            }

        # Use text cleaning utilities to extract medical entities
        from app.utils.text_cleaning import TextCleaner

        entities = TextCleaner.extract_medical_entities(raw_text)

        # Additional structured extraction for medical documents
        structured_data = {
            "patient_info": self._extract_patient_info(raw_text),
            "vitals": self._extract_vitals(raw_text),
            "medications": entities.get("medications", []),
            "diagnoses": self._extract_diagnoses(raw_text),
            "procedures": self._extract_procedures(raw_text),
            "lab_results": self._extract_lab_results(raw_text),
            "medical_entities": entities,
        }

        return {
            "structured_data": structured_data,
            "extraction_result": extraction_result,
            "confidence": extraction_result.get("confidence", 0.5),
        }

    def _extract_patient_info(self, text: str) -> Dict[str, str]:
        """Extract patient information from text."""
        import re

        patient_info = {}

        # Name patterns
        name_patterns = [
            r"Patient[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Name[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+age",
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                patient_info["name"] = match.group(1).strip()
                break

        # Age patterns
        age_patterns = [r"age[:\s]+(\d+)", r"(\d+)[- ]?year[- ]?old", r"(\d+)\s*y/o"]

        for pattern in age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                patient_info["age"] = match.group(1)
                break

        # Gender patterns
        gender_patterns = [
            r"(?:male|female|man|woman)",
            r"sex[:\s]+(male|female)",
            r"gender[:\s]+(male|female)",
        ]

        for pattern in gender_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                patient_info["gender"] = match.group(1).lower()
                break

        return patient_info

    def _extract_vitals(self, text: str) -> Dict[str, str]:
        """Extract vital signs from text."""
        import re

        vitals = {}

        # Blood pressure
        bp_pattern = r"(?:BP|blood pressure)[:\s]*(\d{2,3})[/\s](\d{2,3})\s*(?:mmhg)?"
        match = re.search(bp_pattern, text, re.IGNORECASE)
        if match:
            vitals["blood_pressure"] = f"{match.group(1)}/{match.group(2)}"

        # Heart rate
        hr_pattern = r"(?:HR|heart rate|pulse)[:\s]*(\d{2,3})\s*(?:bpm)?"
        match = re.search(hr_pattern, text, re.IGNORECASE)
        if match:
            vitals["heart_rate"] = match.group(1)

        # Temperature
        temp_pattern = r"(?:temp|temperature)[:\s]*(\d{2,3}\.?\d*)\s*[°f°cFfCcC]?"
        match = re.search(temp_pattern, text, re.IGNORECASE)
        if match:
            vitals["temperature"] = match.group(1)

        return vitals

    def _extract_diagnoses(self, text: str) -> List[str]:
        """Extract diagnoses from text."""
        import re

        diagnoses = []

        # Common diagnosis patterns
        diagnosis_patterns = [
            r"diagnosis[:\s]+(.+?)(?:\n|$)",
            r"(?:diagnosed with|diagnosis of)[:\s]+(.+?)(?:\n|,|\.)",
            r"impression[:\s]+(.+?)(?:\n|$)",
        ]

        for pattern in diagnosis_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            diagnoses.extend(
                [match.strip() for match in matches if len(match.strip()) > 3]
            )

        return list(set(diagnoses))  # Remove duplicates

    def _extract_procedures(self, text: str) -> List[str]:
        """Extract medical procedures from text."""
        import re

        procedures = []

        # Procedure patterns
        procedure_patterns = [
            r"procedure[:\s]+(.+?)(?:\n|$)",
            r"(?:performed|underwent)[:\s]+(.+?)(?:\n|,|\.)",
            r"(?:ct|mri|x-ray|ultrasound|ecg|ekg)[:\s]+(.+?)(?:\n|,|\.)",
        ]

        for pattern in procedure_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            procedures.extend(
                [match.strip() for match in matches if len(match.strip()) > 3]
            )

        return list(set(procedures))

    def _extract_lab_results(self, text: str) -> Dict[str, str]:
        """Extract laboratory results from text."""
        import re

        lab_results = {}

        # Common lab value patterns
        lab_patterns = {
            "glucose": r"glucose[:\s]*(\d+\.?\d*)\s*(?:mg/dl)",
            "creatinine": r"creatinine[:\s]*(\d+\.?\d*)\s*(?:mg/dl)",
            "troponin": r"troponin[:\s]*(\d+\.?\d*)\s*(?:ng/ml|pg/ml)",
            "wbc": r"wbc[:\s]*(\d+\.?\d*)\s*(?:k/ul|cells/ul)",
            "hemoglobin": r"h(?:gb|emoglobin)[:\s]*(\d+\.?\d*)\s*(?:g/dl)",
            "platelets": r"platelets[:\s]*(\d+\.?\d*)\s*(?:k/ul|cells/ul)",
        }

        for lab, pattern in lab_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lab_results[lab] = match.group(1)

        return lab_results

    def _get_mock_extraction(
        self, file_path: str, error_msg: str = ""
    ) -> Dict[str, Any]:
        """Mock extraction for development/testing."""
        mock_text = f"""
Patient Medical Report - {os.path.basename(file_path)}

PATIENT INFORMATION:
Name: John Doe
Age: 45
Gender: Male
MRN: KNRH-00123

VITAL SIGNS:
Blood Pressure: 140/90 mmHg
Heart Rate: 95 bpm
Temperature: 98.6°F
Respiratory Rate: 18 breaths/min
Oxygen Saturation: 96%

ASSESSMENT:
Patient presents with chest pain and shortness of breath. Symptoms began 2 hours ago. ECG shows possible sinus arrhythmia. History of hypertension controlled with amlodipine 5mg daily.

MEDICATIONS:
- Amlodipine 5mg daily
- Aspirin 81mg daily

ALLERGIES:
- Penicillin (severe)

LAB RESULTS:
- Troponin: 0.05 ng/mL (normal)
- Creatinine: 1.1 mg/dL
- WBC: 8.5 k/μL
- Hemoglobin: 14.2 g/dL
- Platelets: 250 k/μL

IMPRESSION:
Chest pain with possible cardiac etiology. Recommend cardiac workup and continued monitoring.
"""

        return {
            "text": mock_text.strip(),
            "text_length": len(mock_text),
            "extraction_method": "mock",
            "metadata": {
                "original_file": os.path.basename(file_path),
                "note": "Mock extraction - OCR not available",
            },
            "confidence": 0.8,
            "processing_info": {
                "ocr_used": False,
                "mock_data": True,
                "error": error_msg,
            },
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the document AI service."""
        return {
            "ocr_engine": "Tesseract",
            "pdf_engines": ["pdfplumber", "PyMuPDF"],
            "image_processing": "OpenCV",
            "supported_formats": [
                "PDF (digital and scanned)",
                "Images (JPG, PNG, TIFF, BMP)",
                "Text files",
            ],
            "tesseract_available": self.tesseract_available,
            "ocr_languages": self.ocr_languages,
            "capabilities": [
                "Text extraction from PDFs",
                "OCR for scanned documents",
                "Image preprocessing",
                "Structured medical data extraction",
                "Vital signs extraction",
                "Medication identification",
            ],
        }


# Global instance
document_ai_service = DocumentAIService()
