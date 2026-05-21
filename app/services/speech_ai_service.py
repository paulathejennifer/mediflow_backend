"""
Speech AI Service for Mediflow System

This service handles speech-to-text operations using Google Speech Recognition
for medical dictation and voice note transcription.
"""

import asyncio
import os
import tempfile
import logging
from typing import Dict, Any, Optional, Tuple
import speech_recognition as sr
import librosa
import soundfile as sf
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechAIService:
    """Service for speech-to-text operations using Google Speech Recognition."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._initialize_recognizer()

    def _initialize_recognizer(self):
        """Initialize speech recognizer."""
        try:
            logger.info("Initializing Google Speech Recognition")
            # Configure recognizer settings
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            logger.info("Google Speech Recognition initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize speech recognizer: {str(e)}")
    
    async def transcribe_audio(self, audio_path: str, language: str = "en-US") -> Dict[str, Any]:
        """
        Transcribe audio file using Google Speech Recognition.

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en-US' for English US)

        Returns:
            Dictionary with transcription results and metadata
        """
        try:
            # Convert audio to WAV format if needed (Google Speech Recognition requires WAV)
            wav_path = await self._convert_to_wav(audio_path)

            # Get audio duration
            duration = self._get_audio_duration(wav_path)

            # Run transcription in thread pool (Google Speech Recognition is synchronous)
            loop = asyncio.get_event_loop()

            def sync_transcribe():
                with sr.AudioFile(wav_path) as source:
                    # Adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = self.recognizer.record(source)

                    # Use Google Speech Recognition
                    try:
                        transcript = self.recognizer.recognize_google(audio_data, language=language)
                        return transcript, True
                    except sr.UnknownValueError:
                        return "", False
                    except sr.RequestError as e:
                        raise Exception(f"Google Speech Recognition service error: {str(e)}")

            transcript, success = await loop.run_in_executor(None, sync_transcribe)

            # Clean up converted WAV file if different from original
            if wav_path != audio_path and os.path.exists(wav_path):
                os.remove(wav_path)

            if not success or not transcript:
                raise Exception("Speech recognition failed - could not understand audio")

            word_count = len(transcript.split())

            return {
                "transcript": transcript,
                "word_count": word_count,
                "duration_seconds": duration,
                "confidence": 0.85,  # Google doesn't provide confidence, using default
                "language": language,
                "model_used": "Google Speech Recognition",
                "word_timestamps": [],  # Google doesn't provide word timestamps
                "segments": [],
                "processing_info": {
                    "audio_converted": wav_path != audio_path,
                    "service": "Google Speech Recognition"
                }
            }

        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    async def _convert_to_wav(self, audio_path: str) -> str:
        """
        Convert audio file to WAV format for Google Speech Recognition.

        Args:
            audio_path: Original audio file path

        Returns:
            Path to WAV file
        """
        try:
            # Check if already WAV
            if audio_path.lower().endswith('.wav'):
                return audio_path

            # Create temporary WAV file
            temp_dir = tempfile.gettempdir()
            wav_path = os.path.join(temp_dir, f"converted_{os.path.splitext(os.path.basename(audio_path))[0]}.wav")

            # Load audio
            y, sr_rate = librosa.load(audio_path, sr=None)

            # Save as WAV
            sf.write(wav_path, y, sr_rate)

            logger.info(f"Audio converted to WAV: {audio_path} -> {wav_path}")
            return wav_path

        except Exception as e:
            logger.warning(f"Audio conversion failed: {str(e)}")
            return audio_path

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            y, sr_rate = librosa.load(audio_path, sr=None)
            duration = len(y) / sr_rate
            return round(duration, 2)
        except Exception:
            return 0.0
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the speech recognition service being used."""
        return {
            "provider": "Google",
            "service": "Google Speech Recognition",
            "model_type": "Cloud-based Speech Recognition",
            "capabilities": [
                "Medical dictation",
                "Multi-language support",
                "Real-time transcription",
                "High accuracy transcription",
                "Noise robust processing"
            ],
            "is_configured": True,
            "supported_languages": [
                "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR",
                "zh-CN", "ja-JP", "ko-KR", "ru-RU", "ar-SA", "hi-IN", "tr-TR"
            ],
            "recommended_settings": {
                "sample_rate": 16000,
                "channels": 1,  # Mono
                "audio_format": "wav",
                "max_file_size_mb": 10,
                "optimal_duration": "30 seconds to 2 minutes"
            }
        }

# Global instance
speech_ai_service = SpeechAIService()
