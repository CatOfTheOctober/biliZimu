"""Basic setup verification tests."""

import pytest
from bilibili_extractor import __version__
from bilibili_extractor.core.models import VideoInfo, TextSegment, ExtractionResult
from bilibili_extractor.core.config import Config, ConfigLoader


def test_version():
    """Test that version is defined."""
    assert __version__ == "1.0.0"


def test_video_info_creation():
    """Test VideoInfo dataclass creation."""
    video = VideoInfo(
        video_id="BV1xx411c7mD",
        title="Test Video",
        duration=300,
        has_subtitle=True,
        url="https://www.bilibili.com/video/BV1xx411c7mD",
    )
    assert video.video_id == "BV1xx411c7mD"
    assert video.duration == 300


def test_text_segment_creation():
    """Test TextSegment dataclass creation."""
    segment = TextSegment(
        start_time=0.0, end_time=5.0, text="Hello world", confidence=0.95, source="subtitle"
    )
    assert segment.start_time == 0.0
    assert segment.end_time == 5.0
    assert segment.text == "Hello world"


def test_config_defaults():
    """Test Config default values."""
    config = Config()
    assert config.temp_dir == "./temp"
    assert config.output_dir == "./output"
    assert config.log_level == "INFO"
    assert config.asr_engine == "funasr"
    assert config.output_format == "srt"


def test_config_validation_valid():
    """Test config validation with valid values."""
    config = Config(
        log_level="DEBUG", video_quality="1080P", asr_engine="whisper", output_format="json"
    )
    assert ConfigLoader.validate_config(config) is True


def test_config_validation_invalid_log_level():
    """Test config validation with invalid log level uses default."""
    config = Config(log_level="INVALID")
    assert ConfigLoader.validate_config(config) is True
    # After validation, invalid value should be replaced with default
    assert config.log_level == "INFO"


def test_config_validation_invalid_quality():
    """Test config validation with invalid video quality uses default."""
    config = Config(video_quality="4K")
    assert ConfigLoader.validate_config(config) is True
    # After validation, invalid value should be replaced with default
    assert config.video_quality == "720P"


def test_config_validation_invalid_asr_engine():
    """Test config validation with invalid ASR engine uses default."""
    config = Config(asr_engine="invalid")
    assert ConfigLoader.validate_config(config) is True
    # After validation, invalid value should be replaced with default
    assert config.asr_engine == "funasr"


def test_config_validation_invalid_format():
    """Test config validation with invalid output format uses default."""
    config = Config(output_format="pdf")
    assert ConfigLoader.validate_config(config) is True
    # After validation, invalid value should be replaced with default
    assert config.output_format == "srt"
