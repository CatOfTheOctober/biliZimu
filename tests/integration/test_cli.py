"""Integration tests for CLI functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from bilibili_extractor.cli import main, parse_arguments, load_config, format_time, save_output, display_summary
from bilibili_extractor.core.models import ExtractionResult, VideoInfo, TextSegment


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_parse_arguments_with_url(self):
        """Test parsing with URL argument."""
        with patch('sys.argv', ['prog', 'https://www.bilibili.com/video/BV1xx411c7mD']):
            args = parse_arguments()
            assert args.url == 'https://www.bilibili.com/video/BV1xx411c7mD'

    def test_parse_arguments_with_format(self):
        """Test parsing with format option."""
        with patch('sys.argv', ['prog', 'url', '--format', 'json']):
            args = parse_arguments()
            assert args.format == 'json'

    def test_parse_arguments_with_output(self):
        """Test parsing with output option."""
        with patch('sys.argv', ['prog', 'url', '--output', 'test.srt']):
            args = parse_arguments()
            assert args.output == 'test.srt'


class TestConfigLoading:
    """Test configuration loading."""

    def test_load_config_without_file(self):
        """Test loading config without config file."""
        with patch('sys.argv', ['prog', 'url']):
            args = parse_arguments()
            config = load_config(args)
            assert config.output_format == 'srt'
            assert config.log_level == 'INFO'

    def test_load_config_with_cli_override(self):
        """Test CLI arguments override default config."""
        with patch('sys.argv', ['prog', 'url', '--format', 'json', '--log-level', 'DEBUG']):
            args = parse_arguments()
            config = load_config(args)
            assert config.output_format == 'json'
            assert config.log_level == 'DEBUG'


class TestTimeFormatting:
    """Test time formatting utility."""

    def test_format_time_seconds(self):
        """Test formatting time in seconds."""
        assert format_time(3.45) == "3.45s"
        assert format_time(45.0) == "45.00s"

    def test_format_time_minutes(self):
        """Test formatting time in minutes."""
        assert format_time(135.0) == "2m 15s"
        assert format_time(90.0) == "1m 30s"

    def test_format_time_hours(self):
        """Test formatting time in hours."""
        assert format_time(3665.0) == "1h 1m"
        assert format_time(7200.0) == "2h 0m"


class TestOutputSaving:
    """Test output saving functionality."""

    def test_save_output_srt(self, tmp_path):
        """Test saving output in SRT format."""
        segments = [
            TextSegment(0.0, 2.5, "Hello world", 1.0, "subtitle"),
            TextSegment(2.5, 5.0, "Test subtitle", 1.0, "subtitle")
        ]
        result = ExtractionResult(
            video_info=VideoInfo("BV123", "Test", 10, True, "url"),
            segments=segments,
            method="subtitle",
            processing_time=1.0,
            metadata={}
        )
        
        output_path = tmp_path / "test.srt"
        save_output(result, output_path, "srt")
        
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "Hello world" in content
        assert "Test subtitle" in content

    def test_save_output_json(self, tmp_path):
        """Test saving output in JSON format."""
        segments = [TextSegment(0.0, 2.5, "Hello", 1.0, "subtitle")]
        result = ExtractionResult(
            video_info=VideoInfo("BV123", "Test", 10, True, "url"),
            segments=segments,
            method="subtitle",
            processing_time=1.0,
            metadata={}
        )
        
        output_path = tmp_path / "test.json"
        save_output(result, output_path, "json")
        
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert '"video_id": "BV123"' in content


class TestSummaryDisplay:
    """Test summary display functionality."""

    def test_display_summary(self, capsys):
        """Test summary report display."""
        segments = [TextSegment(0.0, 2.5, "Test", 1.0, "subtitle")]
        result = ExtractionResult(
            video_info=VideoInfo("BV123", "Test", 10, True, "url"),
            segments=segments,
            method="subtitle",
            processing_time=1.5,
            metadata={}
        )
        
        output_path = Path("output/test.srt")
        display_summary(result, output_path, 2.0)
        
        captured = capsys.readouterr()
        assert "BV123" in captured.out
        assert "Subtitle" in captured.out
        assert "1.50s" in captured.out
        assert "2.00s" in captured.out


class TestCLIMainFunction:
    """Test main CLI function."""

    def test_main_without_arguments(self):
        """Test main function without URL or batch."""
        with patch('sys.argv', ['prog']):
            exit_code = main()
            assert exit_code == 1

    def test_main_with_batch_not_implemented(self):
        """Test main function with batch (not yet implemented)."""
        with patch('sys.argv', ['prog', '--batch', 'urls.txt']):
            exit_code = main()
            assert exit_code == 1


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_url_error(self):
        """Test handling of invalid URL."""
        with patch('sys.argv', ['prog', 'invalid-url']):
            exit_code = main()
            assert exit_code == 1

    def test_config_file_not_found(self):
        """Test handling of missing config file."""
        with patch('sys.argv', ['prog', 'url', '--config', 'nonexistent.yaml']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
