"""
Audio Processing Utilities for Mediflow System

This module provides utilities for audio processing, normalization,
and quality assessment for voice notes and transcription.
"""

import os
import wave
from typing import Dict, Any
import subprocess
from pathlib import Path


class AudioProcessor:
    """Utility class for audio processing operations."""

    # Supported audio formats
    SUPPORTED_FORMATS = {
        ".wav": "wav",
        ".mp3": "mp3",
        ".m4a": "m4a",
        ".ogg": "ogg",
        ".flac": "flac",
    }

    # Target audio parameters for transcription
    TARGET_SAMPLE_RATE = 16000  # 16kHz for speech recognition
    TARGET_CHANNELS = 1  # Mono
    TARGET_BIT_DEPTH = 16  # 16-bit

    @staticmethod
    def get_audio_info(file_path: str) -> Dict[str, Any]:
        """
        Get comprehensive audio file information.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio file information
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        file_ext = Path(file_path).suffix.lower()

        if file_ext == ".wav":
            return AudioProcessor._get_wav_info(file_path)
        else:
            # For other formats, use ffprobe if available
            return AudioProcessor._get_ffprobe_info(file_path)

    @staticmethod
    def _get_wav_info(file_path: str) -> Dict[str, Any]:
        """Get WAV file information."""
        try:
            with wave.open(file_path, "rb") as wav_file:
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()

                duration = n_frames / frame_rate if frame_rate > 0 else 0
                bit_depth = sample_width * 8
                file_size = os.path.getsize(file_path)

                return {
                    "format": "wav",
                    "channels": n_channels,
                    "sample_rate": frame_rate,
                    "bit_depth": bit_depth,
                    "duration_seconds": duration,
                    "frame_count": n_frames,
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                    "bitrate_kbps": round((file_size * 8) / (duration * 1000), 2)
                    if duration > 0
                    else 0,
                }
        except Exception as e:
            raise ValueError(f"Error reading WAV file: {str(e)}")

    @staticmethod
    def _get_ffprobe_info(file_path: str) -> Dict[str, Any]:
        """Get audio info using ffprobe (if available)."""
        try:
            # Use ffprobe to get audio information
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                raise ValueError(f"ffprobe failed: {result.stderr}")

            import json

            probe_data = json.loads(result.stdout)

            # Extract audio stream information
            audio_stream = None
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break

            if not audio_stream:
                raise ValueError("No audio stream found in file")

            # Extract format information
            format_info = probe_data.get("format", {})

            return {
                "format": audio_stream.get("codec_name", "unknown"),
                "channels": int(audio_stream.get("channels", 0)),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "bit_depth": int(audio_stream.get("bits_per_sample", 0)),
                "duration_seconds": float(audio_stream.get("duration", 0)),
                "file_size_bytes": int(format_info.get("size", 0)),
                "file_size_mb": round(
                    int(format_info.get("size", 0)) / (1024 * 1024), 2
                ),
                "bitrate_kbps": int(format_info.get("bit_rate", 0)) / 1000
                if format_info.get("bit_rate")
                else 0,
            }

        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            json.JSONDecodeError,
        ) as e:
            # Fallback to basic file info
            file_size = os.path.getsize(file_path)
            return {
                "format": Path(file_path).suffix[1:].lower(),
                "channels": 0,
                "sample_rate": 0,
                "bit_depth": 0,
                "duration_seconds": 0,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "bitrate_kbps": 0,
                "error": f"Could not analyze audio: {str(e)}",
            }

    @staticmethod
    def normalize_audio(input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Normalize audio file for optimal transcription.

        Args:
            input_path: Input audio file path
            output_path: Output audio file path

        Returns:
            Dictionary with normalization results
        """
        try:
            # Get input audio info
            input_info = AudioProcessor.get_audio_info(input_path)

            # Use ffmpeg for normalization if available
            if AudioProcessor._check_ffmpeg_available():
                return AudioProcessor._normalize_with_ffmpeg(
                    input_path, output_path, input_info
                )
            else:
                # Fallback to basic processing
                return AudioProcessor._normalize_basic(
                    input_path, output_path, input_info
                )

        except Exception as e:
            raise ValueError(f"Audio normalization failed: {str(e)}")

    @staticmethod
    def _check_ffmpeg_available() -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def _normalize_with_ffmpeg(
        input_path: str, output_path: str, input_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize audio using ffmpeg."""
        try:
            # Build ffmpeg command for normalization
            cmd = [
                "ffmpeg",
                "-i",
                input_path,
                "-ar",
                str(AudioProcessor.TARGET_SAMPLE_RATE),  # Sample rate
                "-ac",
                str(AudioProcessor.TARGET_CHANNELS),  # Channels
                "-acodec",
                "pcm_s16le",  # 16-bit PCM
                "-y",  # Overwrite output file
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                raise ValueError(f"ffmpeg normalization failed: {result.stderr}")

            # Get output info
            output_info = AudioProcessor.get_audio_info(output_path)

            return {
                "success": True,
                "method": "ffmpeg",
                "input_info": input_info,
                "output_info": output_info,
                "changes": {
                    "sample_rate": f"{input_info.get('sample_rate', 'N/A')} → {output_info.get('sample_rate', 'N/A')}",
                    "channels": f"{input_info.get('channels', 'N/A')} → {output_info.get('channels', 'N/A')}",
                    "bit_depth": f"{input_info.get('bit_depth', 'N/A')} → {output_info.get('bit_depth', 'N/A')}",
                },
            }

        except subprocess.TimeoutExpired:
            raise ValueError("ffmpeg normalization timed out")

    @staticmethod
    def _normalize_basic(
        input_path: str, output_path: str, input_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic audio normalization (fallback)."""
        # For now, just copy the file as fallback
        # In a real implementation, you'd use a Python audio library
        import shutil

        shutil.copy2(input_path, output_path)

        output_info = AudioProcessor.get_audio_info(output_path)

        return {
            "success": True,
            "method": "basic_copy",
            "input_info": input_info,
            "output_info": output_info,
            "changes": "File copied (ffmpeg not available for processing)",
        }

    @staticmethod
    def assess_audio_quality(file_path: str) -> Dict[str, Any]:
        """
        Assess audio quality for transcription suitability.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with quality assessment
        """
        try:
            audio_info = AudioProcessor.get_audio_info(file_path)

            quality_score = 100
            issues = []
            recommendations = []

            # Check sample rate
            if audio_info.get("sample_rate", 0) < 16000:
                quality_score -= 20
                issues.append("Low sample rate")
                recommendations.append("Resample to 16kHz or higher")
            elif audio_info.get("sample_rate", 0) > 48000:
                quality_score -= 10
                issues.append("Very high sample rate")
                recommendations.append("Consider downsampling to 16kHz")

            # Check channels
            if audio_info.get("channels", 0) > 1:
                quality_score -= 15
                issues.append("Multi-channel audio")
                recommendations.append("Convert to mono for better transcription")

            # Check bit depth
            if audio_info.get("bit_depth", 0) < 16:
                quality_score -= 15
                issues.append("Low bit depth")
                recommendations.append("Use 16-bit or higher audio")

            # Check duration
            duration = audio_info.get("duration_seconds", 0)
            if duration < 1:
                quality_score -= 30
                issues.append("Very short duration")
                recommendations.append("Audio should be at least 1 second long")
            elif duration > 600:  # 10 minutes
                quality_score -= 10
                issues.append("Very long duration")
                recommendations.append("Consider splitting long recordings")

            # Check file size
            file_size_mb = audio_info.get("file_size_mb", 0)
            if file_size_mb > 50:
                quality_score -= 10
                issues.append("Large file size")
                recommendations.append("Consider compression or splitting")

            # Determine overall quality
            if quality_score >= 80:
                quality_level = "Excellent"
            elif quality_score >= 60:
                quality_level = "Good"
            elif quality_score >= 40:
                quality_level = "Fair"
            else:
                quality_level = "Poor"

            return {
                "quality_score": max(0, quality_score),
                "quality_level": quality_level,
                "suitable_for_transcription": quality_score >= 50,
                "issues": issues,
                "recommendations": recommendations,
                "audio_info": audio_info,
            }

        except Exception as e:
            return {
                "quality_score": 0,
                "quality_level": "Unknown",
                "suitable_for_transcription": False,
                "issues": [f"Error analyzing audio: {str(e)}"],
                "recommendations": ["Check audio file format and integrity"],
                "audio_info": {},
            }

    @staticmethod
    def convert_format(
        input_path: str, output_path: str, target_format: str = "wav"
    ) -> Dict[str, Any]:
        """
        Convert audio file to different format.

        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            target_format: Target format (wav, mp3, etc.)

        Returns:
            Dictionary with conversion results
        """
        try:
            if not AudioProcessor._check_ffmpeg_available():
                raise ValueError("ffmpeg not available for format conversion")

            # Map formats to codecs
            codec_map = {
                "wav": "pcm_s16le",
                "mp3": "libmp3lame",
                "m4a": "aac",
                "ogg": "libvorbis",
            }

            codec = codec_map.get(target_format.lower())
            if not codec:
                raise ValueError(f"Unsupported target format: {target_format}")

            # Build conversion command
            cmd = [
                "ffmpeg",
                "-i",
                input_path,
                "-acodec",
                codec,
                "-y",  # Overwrite output file
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                raise ValueError(f"Format conversion failed: {result.stderr}")

            # Get file info
            input_info = AudioProcessor.get_audio_info(input_path)
            output_info = AudioProcessor.get_audio_info(output_path)

            return {
                "success": True,
                "conversion": f"{input_info.get('format', 'unknown')} → {target_format}",
                "input_info": input_info,
                "output_info": output_info,
                "size_change": f"{input_info.get('file_size_mb', 0)}MB → {output_info.get('file_size_mb', 0)}MB",
            }

        except subprocess.TimeoutExpired:
            raise ValueError("Format conversion timed out")

    @staticmethod
    def extract_audio_segment(
        input_path: str, output_path: str, start_seconds: float, duration_seconds: float
    ) -> Dict[str, Any]:
        """
        Extract a segment from audio file.

        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            start_seconds: Start time in seconds
            duration_seconds: Duration in seconds

        Returns:
            Dictionary with extraction results
        """
        try:
            if not AudioProcessor._check_ffmpeg_available():
                raise ValueError("ffmpeg not available for audio extraction")

            # Build extraction command
            cmd = [
                "ffmpeg",
                "-i",
                input_path,
                "-ss",
                str(start_seconds),
                "-t",
                str(duration_seconds),
                "-acodec",
                "copy",  # Copy codec without re-encoding
                "-y",  # Overwrite output file
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                raise ValueError(f"Audio extraction failed: {result.stderr}")

            # Get segment info
            segment_info = AudioProcessor.get_audio_info(output_path)

            return {
                "success": True,
                "segment": f"{start_seconds}s - {start_seconds + duration_seconds}s",
                "duration_requested": duration_seconds,
                "duration_actual": segment_info.get("duration_seconds", 0),
                "segment_info": segment_info,
            }

        except subprocess.TimeoutExpired:
            raise ValueError("Audio extraction timed out")

    @staticmethod
    def detect_speech_activity(file_path: str) -> Dict[str, Any]:
        """
        Detect speech activity in audio file (basic implementation).

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with speech activity analysis
        """
        try:
            audio_info = AudioProcessor.get_audio_info(file_path)

            # This is a simplified implementation
            # In production, you'd use libraries like webrtcvad or librosa

            duration = audio_info.get("duration_seconds", 0)

            # Basic heuristics for speech detection
            if duration < 0.5:
                speech_likelihood = "Very Low"
                confidence = 0.1
            elif duration < 2:
                speech_likelihood = "Low"
                confidence = 0.3
            elif duration < 10:
                speech_likelihood = "Medium"
                confidence = 0.6
            else:
                speech_likelihood = "High"
                confidence = 0.8

            return {
                "speech_likelihood": speech_likelihood,
                "confidence": confidence,
                "duration_seconds": duration,
                "estimated_speech_ratio": min(0.9, confidence),  # Simplified
                "method": "basic_heuristics",
                "note": "Advanced speech detection requires audio processing libraries",
            }

        except Exception as e:
            return {
                "speech_likelihood": "Unknown",
                "confidence": 0.0,
                "error": f"Speech detection failed: {str(e)}",
            }


# Convenience functions
def get_audio_info(file_path: str) -> Dict[str, Any]:
    """Get audio file information."""
    return AudioProcessor.get_audio_info(file_path)


def normalize_audio(input_path: str, output_path: str) -> Dict[str, Any]:
    """Normalize audio for transcription."""
    return AudioProcessor.normalize_audio(input_path, output_path)


def assess_audio_quality(file_path: str) -> Dict[str, Any]:
    """Assess audio quality for transcription."""
    return AudioProcessor.assess_audio_quality(file_path)


def convert_audio_format(
    input_path: str, output_path: str, target_format: str = "wav"
) -> Dict[str, Any]:
    """Convert audio to different format."""
    return AudioProcessor.convert_format(input_path, output_path, target_format)
