"""Audio extraction from video files."""

import subprocess
import json
from pathlib import Path


class AudioExtractionError(Exception):
    """Exception raised when audio extraction fails."""
    pass


class AudioExtractor:
    """Extract audio from video files using ffmpeg.
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    def extract(self, video_path: Path) -> Path:
        """Extract audio from video using ffmpeg.

        Converts video to WAV format with 16kHz sampling rate and mono channel,
        optimized for ASR processing.

        Args:
            video_path: Path to video file

        Returns:
            Path to extracted audio file (WAV format)

        Raises:
            AudioExtractionError: If extraction fails
            FileNotFoundError: If ffmpeg is not installed or video file doesn't exist
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Generate audio output path (Requirement 4.1)
        audio_path = video_path.parent / f"{video_path.stem}.wav"
        
        # Construct ffmpeg command (Requirements 4.2, 4.3)
        # -i: input file
        # -ar 16000: 16kHz sampling rate (optimal for ASR)
        # -ac 1: mono channel (single channel)
        # -vn: no video (audio only)
        # -y: overwrite output file if exists
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ar", "16000",  # 16kHz sampling rate
            "-ac", "1",      # Mono channel
            "-vn",           # No video
            "-y",            # Overwrite
            str(audio_path)
        ]
        
        try:
            # Execute ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding='utf-8',
                errors='replace'
            )
            
            # Check for errors
            if result.returncode != 0:
                raise AudioExtractionError(
                    f"ffmpeg failed with return code {result.returncode}. "
                    f"Error: {result.stderr}"
                )
            
            # Verify audio file was created (Requirement 4.5)
            if not audio_path.exists():
                raise AudioExtractionError(
                    f"Audio file was not created: {audio_path}"
                )
            
            # Validate audio file (Requirement 4.6)
            if not self.validate_audio(audio_path):
                raise AudioExtractionError(
                    f"Extracted audio file is invalid: {audio_path}"
                )
            
            return audio_path
            
        except FileNotFoundError:
            raise FileNotFoundError(
                "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH."
            )
        except AudioExtractionError:
            raise
        except Exception as e:
            raise AudioExtractionError(f"Error extracting audio: {str(e)}")

    def get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds

        Raises:
            AudioExtractionError: If duration cannot be determined
            FileNotFoundError: If ffprobe is not installed or audio file doesn't exist
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Use ffprobe to get duration (Requirement 4.4)
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse JSON output
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            
            if duration <= 0:
                raise AudioExtractionError(
                    f"Invalid duration: {duration}"
                )
            
            return duration
            
        except FileNotFoundError:
            raise FileNotFoundError(
                "ffprobe not found. Please install ffmpeg (includes ffprobe) and ensure it's in your PATH."
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise AudioExtractionError(
                f"Error parsing ffprobe output: {str(e)}"
            )
        except subprocess.CalledProcessError as e:
            raise AudioExtractionError(
                f"ffprobe failed: {e.stderr}"
            )

    def validate_audio(self, audio_path: Path) -> bool:
        """Validate audio file integrity using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            True if valid, False otherwise
        """
        if not audio_path.exists():
            return False
        
        # Use ffprobe to validate audio file (Requirement 4.6)
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse JSON output
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            
            # Valid audio should have positive duration
            return duration > 0
            
        except Exception:
            # Any error means invalid audio
            return False
