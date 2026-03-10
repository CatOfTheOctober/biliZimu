"""Unit tests for AudioExtractor module."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from bilibili_extractor.modules.audio_extractor import AudioExtractor, AudioExtractionError


@pytest.fixture
def extractor():
    """Create an AudioExtractor instance."""
    return AudioExtractor()


@pytest.fixture
def mock_video_file(tmp_path):
    """Create a mock video file."""
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()
    return video_file


class TestAudioExtractorExtract:
    """Test AudioExtractor.extract() method."""

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_success(self, mock_run, extractor, mock_video_file):
        """Test successful audio extraction."""
        # Mock ffmpeg success
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Mock audio file creation
        audio_path = mock_video_file.parent / f"{mock_video_file.stem}.wav"
        audio_path.touch()
        
        # Mock validate_audio to return True
        with patch.object(extractor, 'validate_audio', return_value=True):
            # Extract audio
            result = extractor.extract(mock_video_file)
        
        # Verify result
        assert result == audio_path
        assert result.exists()
        
        # Verify ffmpeg command (first call is ffmpeg, second might be ffprobe for validation)
        ffmpeg_calls = [call for call in mock_run.call_args_list if call[0][0][0] == "ffmpeg"]
        assert len(ffmpeg_calls) >= 1
        call_args = ffmpeg_calls[0][0][0]
        assert call_args[0] == "ffmpeg"
        assert "-i" in call_args
        assert str(mock_video_file) in call_args
        assert "-ar" in call_args
        assert "16000" in call_args  # 16kHz sampling rate
        assert "-ac" in call_args
        assert "1" in call_args  # Mono channel
        assert "-vn" in call_args  # No video

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_video_not_found(self, mock_run, extractor, tmp_path):
        """Test extraction when video file doesn't exist."""
        non_existent_file = tmp_path / "non_existent.mp4"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            extractor.extract(non_existent_file)
        
        assert "Video file not found" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_ffmpeg_not_found(self, mock_run, extractor, mock_video_file):
        """Test extraction when ffmpeg is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(FileNotFoundError) as exc_info:
            extractor.extract(mock_video_file)
        
        assert "ffmpeg not found" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_ffmpeg_fails(self, mock_run, extractor, mock_video_file):
        """Test extraction when ffmpeg command fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: Invalid video format"
        )
        
        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.extract(mock_video_file)
        
        assert "ffmpeg failed" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_audio_file_not_created(self, mock_run, extractor, mock_video_file):
        """Test extraction when audio file is not created."""
        # Mock ffmpeg success but don't create audio file
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.extract(mock_video_file)
        
        assert "Audio file was not created" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_creates_wav_file(self, mock_run, extractor, mock_video_file):
        """Test that extraction creates WAV file with correct name."""
        # Mock ffmpeg success
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Mock audio file creation
        audio_path = mock_video_file.parent / f"{mock_video_file.stem}.wav"
        audio_path.touch()
        
        # Mock validate_audio to return True
        with patch.object(extractor, 'validate_audio', return_value=True):
            # Extract audio
            result = extractor.extract(mock_video_file)
        
        # Verify WAV extension
        assert result.suffix == ".wav"
        assert result.stem == mock_video_file.stem


class TestAudioExtractorGetDuration:
    """Test AudioExtractor.get_audio_duration() method."""

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_get_duration_success(self, mock_run, extractor, tmp_path):
        """Test successful duration retrieval."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock ffprobe output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"format": {"duration": "123.45"}})
        )
        
        # Get duration
        duration = extractor.get_audio_duration(audio_file)
        
        # Verify result
        assert duration == 123.45
        
        # Verify ffprobe command
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffprobe"
        assert "-show_entries" in call_args
        assert "format=duration" in call_args
        assert "-of" in call_args
        assert "json" in call_args

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_get_duration_audio_not_found(self, mock_run, extractor, tmp_path):
        """Test duration retrieval when audio file doesn't exist."""
        non_existent_file = tmp_path / "non_existent.wav"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            extractor.get_audio_duration(non_existent_file)
        
        assert "Audio file not found" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_get_duration_ffprobe_not_found(self, mock_run, extractor, tmp_path):
        """Test duration retrieval when ffprobe is not installed."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(FileNotFoundError) as exc_info:
            extractor.get_audio_duration(audio_file)
        
        assert "ffprobe not found" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_get_duration_invalid_json(self, mock_run, extractor, tmp_path):
        """Test duration retrieval with invalid JSON output."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock invalid JSON output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json"
        )
        
        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.get_audio_duration(audio_file)
        
        assert "Error parsing ffprobe output" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_get_duration_zero_duration(self, mock_run, extractor, tmp_path):
        """Test duration retrieval with zero duration."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock zero duration
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"format": {"duration": "0"}})
        )
        
        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.get_audio_duration(audio_file)
        
        assert "Invalid duration" in str(exc_info.value)

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_get_duration_negative_duration(self, mock_run, extractor, tmp_path):
        """Test duration retrieval with negative duration."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock negative duration
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"format": {"duration": "-10"}})
        )
        
        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.get_audio_duration(audio_file)
        
        assert "Invalid duration" in str(exc_info.value)


class TestAudioExtractorValidate:
    """Test AudioExtractor.validate_audio() method."""

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_validate_valid_audio(self, mock_run, extractor, tmp_path):
        """Test validation of valid audio file."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock valid audio
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"format": {"duration": "123.45"}})
        )
        
        # Validate audio
        result = extractor.validate_audio(audio_file)
        
        assert result is True

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_validate_invalid_audio(self, mock_run, extractor, tmp_path):
        """Test validation of invalid audio file."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock invalid audio (zero duration)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"format": {"duration": "0"}})
        )
        
        # Validate audio
        result = extractor.validate_audio(audio_file)
        
        assert result is False

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_validate_audio_not_found(self, mock_run, extractor, tmp_path):
        """Test validation when audio file doesn't exist."""
        non_existent_file = tmp_path / "non_existent.wav"
        
        # Validate audio
        result = extractor.validate_audio(non_existent_file)
        
        assert result is False

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_validate_ffprobe_fails(self, mock_run, extractor, tmp_path):
        """Test validation when ffprobe fails."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock ffprobe failure
        mock_run.side_effect = Exception("ffprobe error")
        
        # Validate audio
        result = extractor.validate_audio(audio_file)
        
        assert result is False

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_validate_corrupted_audio(self, mock_run, extractor, tmp_path):
        """Test validation of corrupted audio file."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()
        
        # Mock corrupted audio (invalid JSON)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="corrupted output"
        )
        
        # Validate audio
        result = extractor.validate_audio(audio_file)
        
        assert result is False


class TestAudioExtractorParameters:
    """Test audio extraction parameters."""

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_uses_16khz_sampling_rate(self, mock_run, extractor, mock_video_file):
        """Test that extraction uses 16kHz sampling rate."""
        # Mock ffmpeg success
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Mock audio file creation
        audio_path = mock_video_file.parent / f"{mock_video_file.stem}.wav"
        audio_path.touch()
        
        # Mock validate_audio to return True
        with patch.object(extractor, 'validate_audio', return_value=True):
            # Extract audio
            extractor.extract(mock_video_file)
        
        # Verify sampling rate parameter
        ffmpeg_calls = [call for call in mock_run.call_args_list if call[0][0][0] == "ffmpeg"]
        call_args = ffmpeg_calls[0][0][0]
        ar_index = call_args.index("-ar")
        assert call_args[ar_index + 1] == "16000"

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_uses_mono_channel(self, mock_run, extractor, mock_video_file):
        """Test that extraction uses mono channel."""
        # Mock ffmpeg success
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Mock audio file creation
        audio_path = mock_video_file.parent / f"{mock_video_file.stem}.wav"
        audio_path.touch()
        
        # Mock validate_audio to return True
        with patch.object(extractor, 'validate_audio', return_value=True):
            # Extract audio
            extractor.extract(mock_video_file)
        
        # Verify channel parameter
        ffmpeg_calls = [call for call in mock_run.call_args_list if call[0][0][0] == "ffmpeg"]
        call_args = ffmpeg_calls[0][0][0]
        ac_index = call_args.index("-ac")
        assert call_args[ac_index + 1] == "1"

    @patch('bilibili_extractor.modules.audio_extractor.subprocess.run')
    def test_extract_excludes_video(self, mock_run, extractor, mock_video_file):
        """Test that extraction excludes video stream."""
        # Mock ffmpeg success
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Mock audio file creation
        audio_path = mock_video_file.parent / f"{mock_video_file.stem}.wav"
        audio_path.touch()
        
        # Mock validate_audio to return True
        with patch.object(extractor, 'validate_audio', return_value=True):
            # Extract audio
            extractor.extract(mock_video_file)
        
        # Verify no video parameter
        ffmpeg_calls = [call for call in mock_run.call_args_list if call[0][0][0] == "ffmpeg"]
        call_args = ffmpeg_calls[0][0][0]
        assert "-vn" in call_args
