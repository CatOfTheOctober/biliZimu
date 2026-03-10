"""Unit tests for configuration management."""

import pytest
import argparse
import tempfile
import logging
from pathlib import Path
from src.bilibili_extractor.core.config import Config, ConfigLoader


class TestConfig:
    """Test Config dataclass."""

    def test_config_default_values(self):
        """Test that Config has correct default values."""
        config = Config()
        
        assert config.temp_dir == "./temp"
        assert config.output_dir == "./output"
        assert config.log_level == "INFO"
        assert config.keep_temp_files is False
        assert config.cookie_file is None
        assert config.video_quality == "720P"
        assert config.download_threads == 4
        assert config.asr_engine == "funasr"
        assert config.funasr_model == "paraformer-zh"
        assert config.whisper_model == "base"
        assert config.language is None
        assert config.enable_ocr is False
        assert config.ocr_engine == "paddleocr"
        assert config.output_format == "txt"

    def test_config_custom_values(self):
        """Test that Config accepts custom values."""
        config = Config(
            temp_dir="/tmp/custom",
            log_level="DEBUG",
            video_quality="1080P",
            asr_engine="whisper",
            output_format="json"
        )
        
        assert config.temp_dir == "/tmp/custom"
        assert config.log_level == "DEBUG"
        assert config.video_quality == "1080P"
        assert config.asr_engine == "whisper"
        assert config.output_format == "json"


class TestConfigLoaderLoadFromFile:
    """Test ConfigLoader.load_from_file method."""

    def test_load_flat_yaml(self):
        """Test loading configuration from flat YAML structure."""
        yaml_content = """
temp_dir: "/tmp/test"
output_dir: "/output/test"
log_level: "DEBUG"
keep_temp_files: true
video_quality: "1080P"
asr_engine: "whisper"
output_format: "json"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)
        
        try:
            config = ConfigLoader.load_from_file(config_path)
            
            assert config.temp_dir == "/tmp/test"
            assert config.output_dir == "/output/test"
            assert config.log_level == "DEBUG"
            assert config.keep_temp_files is True
            assert config.video_quality == "1080P"
            assert config.asr_engine == "whisper"
            assert config.output_format == "json"
        finally:
            config_path.unlink()

    def test_load_nested_yaml(self):
        """Test loading configuration from nested YAML structure."""
        yaml_content = """
temp_dir: "./temp"
download:
  cookie_file: "/path/to/cookie"
  video_quality: "480P"
  download_threads: 8
asr:
  asr_engine: "whisper"
  whisper_model: "medium"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)
        
        try:
            config = ConfigLoader.load_from_file(config_path)
            
            # Note: nested structure gets flattened
            assert config.temp_dir == "./temp"
            assert config.cookie_file == "/path/to/cookie"
            assert config.video_quality == "480P"
            assert config.download_threads == 8
            assert config.asr_engine == "whisper"
            assert config.whisper_model == "medium"
        finally:
            config_path.unlink()


class TestConfigLoaderLoadFromArgs:
    """Test ConfigLoader.load_from_args method."""

    def test_load_from_args_empty(self):
        """Test loading from args with no arguments set."""
        args = argparse.Namespace()
        config = ConfigLoader.load_from_args(args)
        
        # Should return default config
        default = Config()
        assert config.temp_dir == default.temp_dir
        assert config.log_level == default.log_level

    def test_load_from_args_with_values(self):
        """Test loading from args with explicit values."""
        args = argparse.Namespace(
            temp_dir="/tmp/args",
            log_level="DEBUG",
            keep_temp=True,
            cookie="/path/to/cookie",
            video_quality="1080P",
            download_threads=8,
            asr_engine="whisper",
            whisper_model="large",
            format="json",
            enable_ocr=True
        )
        
        config = ConfigLoader.load_from_args(args)
        
        assert config.temp_dir == "/tmp/args"
        assert config.log_level == "DEBUG"
        assert config.keep_temp_files is True
        assert config.cookie_file == "/path/to/cookie"
        assert config.video_quality == "1080P"
        assert config.download_threads == 8
        assert config.asr_engine == "whisper"
        assert config.whisper_model == "large"
        assert config.output_format == "json"
        assert config.enable_ocr is True

    def test_load_from_args_with_none_values(self):
        """Test that None values are not included."""
        args = argparse.Namespace(
            temp_dir="/tmp/args",
            log_level=None,  # Should be ignored
            cookie=None,
            format="json"
        )
        
        config = ConfigLoader.load_from_args(args)
        
        assert config.temp_dir == "/tmp/args"
        assert config.log_level == "INFO"  # Default value
        assert config.output_format == "json"


class TestConfigLoaderMergeConfigs:
    """Test ConfigLoader.merge_configs method."""

    def test_merge_configs_file_only(self):
        """Test merging when only file config has values."""
        file_config = Config(
            temp_dir="/tmp/file",
            log_level="DEBUG",
            video_quality="1080P"
        )
        args_config = Config()  # All defaults
        
        merged = ConfigLoader.merge_configs(file_config, args_config)
        
        assert merged.temp_dir == "/tmp/file"
        assert merged.log_level == "DEBUG"
        assert merged.video_quality == "1080P"

    def test_merge_configs_args_override(self):
        """Test that args override file config."""
        file_config = Config(
            temp_dir="/tmp/file",
            log_level="DEBUG",
            video_quality="1080P",
            asr_engine="funasr"
        )
        args_config = Config(
            log_level="ERROR",  # Override
            video_quality="480P"  # Override
        )
        
        merged = ConfigLoader.merge_configs(file_config, args_config)
        
        assert merged.temp_dir == "/tmp/file"  # From file
        assert merged.log_level == "ERROR"  # From args
        assert merged.video_quality == "480P"  # From args
        assert merged.asr_engine == "funasr"  # From file

    def test_merge_configs_both_have_values(self):
        """Test merging when both configs have non-default values."""
        file_config = Config(
            temp_dir="/tmp/file",
            output_dir="/output/file",
            log_level="WARNING"
        )
        args_config = Config(
            output_dir="/output/args",
            asr_engine="whisper"
        )
        
        merged = ConfigLoader.merge_configs(file_config, args_config)
        
        assert merged.temp_dir == "/tmp/file"
        assert merged.output_dir == "/output/args"  # Args override
        assert merged.log_level == "WARNING"
        assert merged.asr_engine == "whisper"


class TestConfigLoaderValidateConfig:
    """Test ConfigLoader.validate_config method."""

    def test_validate_valid_config(self):
        """Test validation of a valid configuration."""
        config = Config()
        assert ConfigLoader.validate_config(config) is True

    def test_validate_invalid_log_level(self, caplog):
        """Test validation with invalid log level."""
        config = Config(log_level="INVALID")
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.log_level == "INFO"  # Reset to default
        assert "Invalid log_level" in caplog.text

    def test_validate_invalid_video_quality(self, caplog):
        """Test validation with invalid video quality."""
        config = Config(video_quality="4K")
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.video_quality == "720P"  # Reset to default
        assert "Invalid video_quality" in caplog.text

    def test_validate_invalid_asr_engine(self, caplog):
        """Test validation with invalid ASR engine."""
        config = Config(asr_engine="invalid_engine")
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.asr_engine == "funasr"  # Reset to default
        assert "Invalid asr_engine" in caplog.text

    def test_validate_invalid_whisper_model(self, caplog):
        """Test validation with invalid Whisper model."""
        config = Config(whisper_model="ultra")
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.whisper_model == "base"  # Reset to default
        assert "Invalid whisper_model" in caplog.text

    def test_validate_invalid_ocr_engine(self, caplog):
        """Test validation with invalid OCR engine."""
        config = Config(ocr_engine="invalid_ocr")
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.ocr_engine == "paddleocr"  # Reset to default
        assert "Invalid ocr_engine" in caplog.text

    def test_validate_invalid_output_format(self, caplog):
        """Test validation with invalid output format."""
        config = Config(output_format="pdf")
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.output_format == "txt"  # Reset to default
        assert "Invalid output_format" in caplog.text

    def test_validate_invalid_download_threads_zero(self, caplog):
        """Test validation with zero download threads."""
        config = Config(download_threads=0)
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.download_threads == 4  # Reset to default
        assert "Invalid download_threads" in caplog.text

    def test_validate_invalid_download_threads_negative(self, caplog):
        """Test validation with negative download threads."""
        config = Config(download_threads=-5)
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        assert config.download_threads == 4  # Reset to default
        assert "Invalid download_threads" in caplog.text

    def test_validate_multiple_invalid_params(self, caplog):
        """Test validation with multiple invalid parameters."""
        config = Config(
            log_level="TRACE",
            video_quality="8K",
            asr_engine="google",
            output_format="docx",
            download_threads=-1
        )
        
        with caplog.at_level(logging.WARNING):
            result = ConfigLoader.validate_config(config)
        
        assert result is True
        # All should be reset to defaults
        assert config.log_level == "INFO"
        assert config.video_quality == "720P"
        assert config.asr_engine == "funasr"
        assert config.output_format == "txt"
        assert config.download_threads == 4
        
        # Should have multiple warnings
        assert caplog.text.count("Invalid") >= 5

    def test_validate_all_valid_values(self):
        """Test validation with all valid edge case values."""
        config = Config(
            log_level="ERROR",
            video_quality="480P",
            asr_engine="whisper",
            whisper_model="large",
            ocr_engine="tesseract",
            output_format="markdown",
            download_threads=1
        )
        
        result = ConfigLoader.validate_config(config)
        
        assert result is True
        # Values should remain unchanged
        assert config.log_level == "ERROR"
        assert config.video_quality == "480P"
        assert config.asr_engine == "whisper"
        assert config.whisper_model == "large"
        assert config.ocr_engine == "tesseract"
        assert config.output_format == "markdown"
        assert config.download_threads == 1
