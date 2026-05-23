"""
MRN Generator Utilities for Mediflow System

This module provides utility functions for MRN generation, validation,
and formatting that complement the MRN service.
"""

import re
from typing import Tuple, Optional, List
from datetime import datetime


class MRNGenerator:
    """Utility class for MRN generation and validation."""

    @staticmethod
    def generate_facility_code(facility_name: str) -> str:
        """
        Generate facility code from facility name.

        Args:
            facility_name: Full facility name

        Returns:
            Generated facility code (e.g., "KNRH" for "Kenyatta National Referral Hospital")
        """
        # Remove common words and extract initials
        common_words = {
            "hospital",
            "medical",
            "center",
            "centre",
            "clinic",
            "health",
            "referral",
            "national",
            "regional",
            "county",
            "district",
            "memorial",
            "general",
            "teaching",
            "university",
        }

        # Split name and filter out common words
        words = facility_name.upper().split()
        meaningful_words = [word for word in words if word not in common_words]

        # If no meaningful words, use first few letters of the name
        if not meaningful_words:
            return facility_name.upper()[:4]

        # Take first letter of each meaningful word
        code = "".join([word[0] for word in meaningful_words[:4]])

        # Ensure minimum length of 3
        if len(code) < 3:
            code = facility_name.upper()[:3]

        # Ensure maximum length of 6
        return code[:6]

    @staticmethod
    def validate_mrn_format(mrn: str) -> bool:
        """
        Validate MRN format.

        Args:
            mrn: MRN string to validate

        Returns:
            True if format is valid
        """
        # Pattern: FACILITYCODE-5digits
        pattern = r"^[A-Z]{2,6}-\d{5}$"
        return bool(re.match(pattern, mrn))

    @staticmethod
    def parse_mrn(mrn: str) -> Tuple[str, int]:
        """
        Parse MRN to extract facility code and patient number.

        Args:
            mrn: MRN string to parse

        Returns:
            Tuple of (facility_code, patient_number)

        Raises:
            ValueError: If MRN format is invalid
        """
        if not MRNGenerator.validate_mrn_format(mrn):
            raise ValueError(f"Invalid MRN format: {mrn}")

        facility_code, patient_number_str = mrn.split("-")
        patient_number = int(patient_number_str)

        return facility_code, patient_number

    @staticmethod
    def format_mrn(facility_code: str, patient_number: int) -> str:
        """
        Format MRN from facility code and patient number.

        Args:
            facility_code: Facility code
            patient_number: Patient number

        Returns:
            Formatted MRN string
        """
        facility_code = facility_code.upper()
        padded_number = str(patient_number).zfill(5)
        return f"{facility_code}-{padded_number}"

    @staticmethod
    def generate_mrn_batch(
        facility_code: str, start_number: int, count: int
    ) -> List[str]:
        """
        Generate a batch of MRNs for testing or bulk operations.

        Args:
            facility_code: Facility code
            start_number: Starting patient number
            count: Number of MRNs to generate

        Returns:
            List of generated MRNs
        """
        mrns = []
        for i in range(count):
            patient_number = start_number + i
            mrn = MRNGenerator.format_mrn(facility_code, patient_number)
            mrns.append(mrn)

        return mrns

    @staticmethod
    def extract_mrn_info(mrn: str) -> dict:
        """
        Extract detailed information from MRN.

        Args:
            mrn: MRN string to analyze

        Returns:
            Dictionary with MRN information
        """
        try:
            facility_code, patient_number = MRNGenerator.parse_mrn(mrn)

            return {
                "mrn": mrn,
                "facility_code": facility_code,
                "patient_number": patient_number,
                "is_valid": True,
                "format_check": "Valid format: FACILITYCODE-00000",
            }
        except ValueError as e:
            return {
                "mrn": mrn,
                "facility_code": None,
                "patient_number": None,
                "is_valid": False,
                "error": str(e),
                "format_check": "Invalid format. Expected: FACILITYCODE-00000",
            }

    @staticmethod
    def suggest_mrn_correction(mrn: str) -> List[str]:
        """
        Suggest corrections for invalid MRN formats.

        Args:
            mrn: Invalid MRN string

        Returns:
            List of suggested corrections
        """
        suggestions = []

        # Remove whitespace and special characters
        clean_mrn = re.sub(r"[^A-Z0-9-]", "", mrn.upper())

        # Check if it looks like it should have a dash
        if "-" not in clean_mrn and len(clean_mrn) >= 3:
            # Try splitting at logical positions
            if len(clean_mrn) >= 7:
                # Assume first 2-6 chars are facility code
                for split_pos in range(2, min(7, len(clean_mrn) - 4)):
                    facility_code = clean_mrn[:split_pos]
                    number_part = clean_mrn[split_pos:]

                    if number_part.isdigit() and len(number_part) <= 5:
                        padded_number = number_part.zfill(5)
                        suggestions.append(f"{facility_code}-{padded_number}")

        # If it has a dash but wrong format
        if "-" in clean_mrn:
            parts = clean_mrn.split("-")
            if len(parts) == 2:
                facility_code, number_part = parts

                # Fix facility code case
                facility_code = facility_code.upper()

                # Fix number padding
                if number_part.isdigit():
                    padded_number = number_part.zfill(5)
                    suggestions.append(f"{facility_code}-{padded_number}")
                else:
                    # Remove non-digits from number part
                    clean_number = re.sub(r"[^0-9]", "", number_part)
                    if clean_number:
                        padded_number = clean_number.zfill(5)
                        suggestions.append(f"{facility_code}-{padded_number}")

        return list(set(suggestions))  # Remove duplicates

    @staticmethod
    def generate_mrn_checksum(facility_code: str, patient_number: int) -> str:
        """
        Generate a simple checksum for MRN validation (optional enhancement).

        Args:
            facility_code: Facility code
            patient_number: Patient number

        Returns:
            Checksum character
        """
        # Simple checksum algorithm
        combined = f"{facility_code}{patient_number}"

        # Calculate sum of character values
        total = 0
        for char in combined:
            if char.isalpha():
                total += ord(char.upper()) - ord("A") + 1
            else:
                total += int(char)

        # Mod 26 for letters
        checksum_char = chr(ord("A") + (total % 26))

        return checksum_char

    @staticmethod
    def generate_mrn_with_checksum(facility_code: str, patient_number: int) -> str:
        """
        Generate MRN with checksum for enhanced validation.

        Args:
            facility_code: Facility code
            patient_number: Patient number

        Returns:
            MRN with checksum (e.g., "KNRH-00001A")
        """
        base_mrn = MRNGenerator.format_mrn(facility_code, patient_number)
        checksum = MRNGenerator.generate_mrn_checksum(facility_code, patient_number)

        return f"{base_mrn}{checksum}"

    @staticmethod
    def validate_mrn_with_checksum(mrn: str) -> bool:
        """
        Validate MRN with checksum.

        Args:
            mrn: MRN string with checksum

        Returns:
            True if valid (including checksum)
        """
        if len(mrn) < 8:  # Minimum length for checksum format
            return False

        # Separate base MRN and checksum
        base_mrn = mrn[:-1]
        provided_checksum = mrn[-1]

        # Validate base format
        if not MRNGenerator.validate_mrn_format(base_mrn):
            return False

        # Calculate expected checksum
        try:
            facility_code, patient_number = MRNGenerator.parse_mrn(base_mrn)
            expected_checksum = MRNGenerator.generate_mrn_checksum(
                facility_code, patient_number
            )

            return provided_checksum.upper() == expected_checksum
        except ValueError:
            return False

    @staticmethod
    def get_mrn_statistics(facility_code: str, current_number: int) -> dict:
        """
        Get statistics about MRN usage for a facility.

        Args:
            facility_code: Facility code
            current_number: Current patient number

        Returns:
            Dictionary with MRN statistics
        """
        return {
            "facility_code": facility_code,
            "current_patient_number": current_number,
            "next_mrn": MRNGenerator.format_mrn(facility_code, current_number + 1),
            "total_patients": current_number,
            "mrn_capacity_remaining": 99999 - current_number,
            "capacity_utilization_percent": (current_number / 99999) * 100,
            "estimated_capacity_exhaustion": (
                f"Number {99999} will be reached in {99999 - current_number} more patients"
            ),
        }


# Convenience functions for common operations
def generate_facility_code(facility_name: str) -> str:
    """Generate facility code from name."""
    return MRNGenerator.generate_facility_code(facility_name)


def validate_mrn(mrn: str) -> bool:
    """Validate MRN format."""
    return MRNGenerator.validate_mrn_format(mrn)


def format_mrn(facility_code: str, patient_number: int) -> str:
    """Format MRN from components."""
    return MRNGenerator.format_mrn(facility_code, patient_number)


def parse_mrn(mrn: str) -> Tuple[str, int]:
    """Parse MRN into components."""
    return MRNGenerator.parse_mrn(mrn)
