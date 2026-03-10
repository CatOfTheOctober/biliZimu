"""Unit tests for TextExtractor."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from bilibili_extractor.core.extractor import TextExtractor
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import TextSegment, ExtractionResult
from bilibili_extractor.modules.url_validator import URLValidationError
from bilibili_extractor.modules.subtitle_fetcher import SubtitleNotFoundError


class TestTextExtractor:
    """Test suite for TextExtractor class."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a test configuration."""
        return Config(
            temp_dir=str(tmp_path / "temp"),
            output_dir=str(tmp_path / "output"),
            log_level="INFO",
            keep_temp_files=False
        )

    @pytest.fixture
    def extractor(self, config):
        """Create a TextExtractor instance."""
        return TextExtractor(config)

    def test_init(self, extractor, config):
        """Test TextExtractor initialization."""
        assert extractor.config == config
        assert extractor.logger is not None
        assert extractor.resource_manager is not None
        assert extractor.subtitle_fetcher is not None

    @patch('bilibili_extractor.core.extractor.URLValidator')
    def test_extract_invalid_url(self, mock_validator, extractor):
        """Test extraction with invalid URL."""
        # Setup mock
        mock_validator.validate.return_value = False
        
        # Test
        with pytest.raises(URLValidationError, match="Invalid URL"):
            extractor.extract("invalid_url")
        
        # Verify
        mock_validator.validate.assert_called_once_with("invalid_url")

    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    def test_extract_with_subtitles_success(self, mock_fetcher_class, mock_validator, extractor, tmp_path):
        """Test successful extraction with official subtitles."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"
        
        # Mock subtitle fetcher instance
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.return_value = True
        
        # Create a temporary subtitle file
        subtitle_file = tmp_path / "test_subtitle.srt"
        subtitle_file.write_text("dummy content")
        mock_fetcher.download_subtitles.return_value = [subtitle_file]
        
        # Mock parsed segments
        mock_segments = [
            TextSegment(start_time=0.0, end_time=2.0, text="Hello", source="subtitle"),
            TextSegment(start_time=2.0, end_time=4.0, text="World", source="subtitle")
        ]
        mock_fetcher.parse_subtitle.return_value = mock_segments
        
        # Replace the extractor's subtitle_fetcher with our mock
        extractor.subtitle_fetcher = mock_fetcher
        
        # Test
        result = extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")
        
        # Verify
        assert isinstance(result, ExtractionResult)
        assert result.video_info.video_id == "BV1xx411c7mD"
        assert result.video_info.has_subtitle is True
        assert result.method == "subtitle"
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello"
        assert result.segments[1].text == "World"
        assert result.processing_time > 0
        assert result.metadata["segment_count"] == 2
        
        # Verify method calls
        mock_validator.validate.assert_called_once()
        mock_validator.extract_video_id.assert_called_once()
        mock_fetcher.check_subtitle_availability.assert_called_once_with("BV1xx411c7mD")
        mock_fetcher.download_subtitles.assert_called_once_with("BV1xx411c7mD")
        mock_fetcher.parse_subtitle.assert_called_once_with(subtitle_file)

    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    @patch('bilibili_extractor.core.extractor.VideoDownloader')
    @patch('bilibili_extractor.core.extractor.AudioExtractor')
    @patch('bilibili_extractor.core.extractor.FunASREngine')
    def test_extract_no_subtitles_uses_asr(self, mock_asr_class, mock_audio_class, mock_video_class, mock_fetcher_class, mock_validator, extractor, tmp_path):
        """Test extraction falls back to ASR when no subtitles are available."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"
        
        # Mock subtitle fetcher - no subtitles
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.return_value = False
        extractor.subtitle_fetcher = mock_fetcher
        
        # Mock video downloader
        video_file = tmp_path / "video.mp4"
        video_file.touch()
        mock_video = Mock()
        mock_video.download.return_value = video_file
        extractor.video_downloader = mock_video
        
        # Mock audio extractor
        audio_file = tmp_path / "audio.wav"
        audio_file.touch()
        mock_audio = Mock()
        mock_audio.extract.return_value = audio_file
        extractor.audio_extractor = mock_audio
        
        # Mock ASR engine
        mock_asr = Mock()
        mock_segments = [
            TextSegment(start_time=0.0, end_time=2.0, text="ASR result", source="asr")
        ]
        mock_asr.transcribe.return_value = mock_segments
        extractor.asr_engine = mock_asr
        
        # Test
        result = extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")
        
        # Verify
        assert isinstance(result, ExtractionResult)
        assert result.method == "asr"
        assert len(result.segments) == 1
        assert result.segments[0].text == "ASR result"
        
        # Verify workflow
        mock_fetcher.check_subtitle_availability.assert_called_once()
        mock_video.download.assert_called_once()
        mock_audio.extract.assert_called_once()
        mock_asr.transcribe.assert_called_once()

    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    def test_extract_cleanup_on_success(self, mock_fetcher_class, mock_validator, extractor, tmp_path):
        """Test that cleanup is called even on successful extraction."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"
        
        # Mock subtitle fetcher
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.return_value = True
        
        subtitle_file = tmp_path / "test_subtitle.srt"
        subtitle_file.write_text("dummy content")
        mock_fetcher.download_subtitles.return_value = [subtitle_file]
        mock_fetcher.parse_subtitle.return_value = [
            TextSegment(start_time=0.0, end_time=2.0, text="Test", source="subtitle")
        ]
        
        extractor.subtitle_fetcher = mock_fetcher
        
        # Mock resource manager to track cleanup calls
        cleanup_mock = Mock()
        extractor.resource_manager.cleanup = cleanup_mock
        
        # Test
        result = extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")
        
        # Verify cleanup was called
        cleanup_mock.assert_called_once()

    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    def test_extract_cleanup_on_error(self, mock_fetcher_class, mock_validator, extractor):
        """Test that cleanup is called even when an error occurs."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"
        
        # Mock subtitle fetcher to raise an exception
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.side_effect = Exception("Test error")
        
        extractor.subtitle_fetcher = mock_fetcher
        
        # Mock resource manager to track cleanup calls
        cleanup_mock = Mock()
        extractor.resource_manager.cleanup = cleanup_mock
        
        # Test
        with pytest.raises(Exception, match="Test error"):
            extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")
        
        # Verify cleanup was called even on error
        cleanup_mock.assert_called_once()

    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    def test_extract_registers_files_for_cleanup(self, mock_fetcher_class, mock_validator, extractor, tmp_path):
        """Test that downloaded subtitle files are registered for cleanup."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"
        
        # Mock subtitle fetcher
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.return_value = True
        
        subtitle_file = tmp_path / "test_subtitle.srt"
        subtitle_file.write_text("dummy content")
        mock_fetcher.download_subtitles.return_value = [subtitle_file]
        mock_fetcher.parse_subtitle.return_value = [
            TextSegment(start_time=0.0, end_time=2.0, text="Test", source="subtitle")
        ]
        
        extractor.subtitle_fetcher = mock_fetcher
        
        # Mock resource manager to track registered files
        register_mock = Mock()
        extractor.resource_manager.register_file = register_mock
        
        # Test
        result = extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")
        
        # Verify file was registered for cleanup
        register_mock.assert_called_once_with(subtitle_file)

    def test_extract_batch_all_success(self, extractor):
        """Test batch processing with all successful extractions."""
        # Mock successful extractions
        mock_result1 = Mock()
        mock_result1.video_info.video_id = "BV1"
        mock_result2 = Mock()
        mock_result2.video_info.video_id = "BV2"
        
        extractor.extract = Mock(side_effect=[mock_result1, mock_result2])
        
        # Test
        results = extractor.extract_batch([
            "https://www.bilibili.com/video/BV1",
            "https://www.bilibili.com/video/BV2"
        ])
        
        # Verify
        assert len(results) == 2
        assert results[0] == mock_result1
        assert results[1] == mock_result2
        assert extractor.extract.call_count == 2

    def test_extract_batch_partial_failure(self, extractor):
        """Test batch processing with some failures."""
        # Mock: first succeeds, second fails
        mock_result = Mock()
        mock_result.video_info.video_id = "BV1"
        
        extractor.extract = Mock(side_effect=[
            mock_result,
            URLValidationError("Invalid URL")
        ])
        
        # Test - should not raise exception
        results = extractor.extract_batch([
            "https://www.bilibili.com/video/BV1",
            "invalid_url"
        ])
        
        # Verify - only successful result returned
        assert len(results) == 1
        assert results[0] == mock_result
        assert extractor.extract.call_count == 2

    def test_extract_batch_all_failure(self, extractor):
        """Test batch processing with all failures."""
        # Mock all failures
        extractor.extract = Mock(side_effect=URLValidationError("Invalid URL"))
        
        # Test - should not raise exception
        results = extractor.extract_batch([
            "invalid_url1",
            "invalid_url2"
        ])
        
        # Verify - empty results
        assert len(results) == 0
        assert extractor.extract.call_count == 2

    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    def test_extract_no_subtitles_no_asr_library(self, mock_fetcher_class, mock_validator, extractor):
        """Test extraction fails gracefully when no subtitles and ASR library not available."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"
        
        # Mock subtitle fetcher - no subtitles
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.return_value = False
        extractor.subtitle_fetcher = mock_fetcher
        
        # Set ASR engine to None (simulating library not available)
        extractor.asr_engine = None
        
        # Test - should raise SubtitleNotFoundError with helpful message
        with pytest.raises(SubtitleNotFoundError) as exc_info:
            extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")
        
        # Verify error message contains installation instructions
        error_msg = str(exc_info.value)
        assert "No subtitles found" in error_msg
        assert "ASR is not available" in error_msg
        assert "pip install funasr" in error_msg or "pip install openai-whisper" in error_msg
        
        # Verify workflow stopped at subtitle check
        mock_fetcher.check_subtitle_availability.assert_called_once()
    @patch('bilibili_extractor.core.extractor.URLValidator')
    @patch('bilibili_extractor.core.extractor.SubtitleFetcher')
    def test_extract_no_subtitles_no_asr_library(self, mock_fetcher_class, mock_validator, extractor):
        """Test extraction fails gracefully when no subtitles and ASR library not available."""
        # Setup mocks
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        # Mock subtitle fetcher - no subtitles
        mock_fetcher = Mock()
        mock_fetcher.check_subtitle_availability.return_value = False
        extractor.subtitle_fetcher = mock_fetcher

        # Set ASR engine to None (simulating library not available)
        extractor.asr_engine = None

        # Test - should raise SubtitleNotFoundError with helpful message
        with pytest.raises(SubtitleNotFoundError) as exc_info:
            extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")

        # Verify error message contains installation instructions
        error_msg = str(exc_info.value)
        assert "No subtitles found" in error_msg
        assert "ASR is not available" in error_msg
        assert "pip install funasr" in error_msg or "pip install openai-whisper" in error_msg

        # Verify workflow stopped at subtitle check
        mock_fetcher.check_subtitle_availability.assert_called_once()


