"""Unit tests for OutputFormatter."""

import json
import pytest
from bilibili_extractor.modules.output_formatter import OutputFormatter
from bilibili_extractor.core.models import TextSegment, ExtractionResult, VideoInfo


class TestOutputFormatter:
    """Test suite for OutputFormatter class."""

    @pytest.fixture
    def sample_segments(self):
        """Create sample text segments for testing."""
        return [
            TextSegment(
                start_time=1.0,
                end_time=3.0,
                text="这是第一句字幕",
                confidence=1.0,
                source="subtitle"
            ),
            TextSegment(
                start_time=3.5,
                end_time=5.0,
                text="这是第二句字幕",
                confidence=0.95,
                source="asr"
            ),
            TextSegment(
                start_time=5.5,
                end_time=8.0,
                text="这是第三句字幕",
                confidence=1.0,
                source="subtitle"
            )
        ]

    @pytest.fixture
    def sample_result(self, sample_segments):
        """Create sample extraction result for testing."""
        video_info = VideoInfo(
            video_id="BV1xx411c7mD",
            title="测试视频",
            duration=600,
            has_subtitle=True,
            url="https://www.bilibili.com/video/BV1xx411c7mD"
        )
        
        return ExtractionResult(
            video_info=video_info,
            segments=sample_segments,
            method="subtitle",
            processing_time=1.5,
            metadata={"extractor_version": "1.0.0"}
        )

    def test_to_srt_basic(self, sample_segments):
        """Test basic SRT format conversion."""
        result = OutputFormatter.to_srt(sample_segments)
        
        # Check structure
        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert "00:00:01,000 --> 00:00:03,000" in result
        assert "00:00:03,500 --> 00:00:05,000" in result
        assert "这是第一句字幕" in result
        assert "这是第二句字幕" in result

    def test_to_srt_empty(self):
        """Test SRT conversion with empty segments."""
        result = OutputFormatter.to_srt([])
        assert result == ""

    def test_to_srt_timestamp_format(self):
        """Test SRT timestamp formatting."""
        segments = [
            TextSegment(
                start_time=3661.123,  # 1:01:01.123
                end_time=3665.456,    # 1:01:05.456
                text="测试时间戳",
                confidence=1.0,
                source="subtitle"
            )
        ]
        
        result = OutputFormatter.to_srt(segments)
        assert "01:01:01,123 --> 01:01:05,456" in result

    def test_to_json_basic(self, sample_result):
        """Test basic JSON format conversion."""
        result = OutputFormatter.to_json(sample_result)
        
        # Parse JSON
        data = json.loads(result)
        
        # Check structure
        assert "video_info" in data
        assert "segments" in data
        assert "method" in data
        assert "processing_time" in data
        assert "metadata" in data
        
        # Check video info
        assert data["video_info"]["video_id"] == "BV1xx411c7mD"
        assert data["video_info"]["title"] == "测试视频"
        
        # Check segments
        assert len(data["segments"]) == 3
        assert data["segments"][0]["text"] == "这是第一句字幕"
        assert data["segments"][0]["start_time"] == 1.0
        assert data["segments"][0]["end_time"] == 3.0

    def test_to_json_preserves_chinese(self, sample_result):
        """Test that JSON preserves Chinese characters."""
        result = OutputFormatter.to_json(sample_result)
        
        # Should contain Chinese characters directly, not escaped
        assert "这是第一句字幕" in result
        assert "测试视频" in result

    def test_to_txt_basic(self, sample_segments):
        """Test basic TXT format conversion."""
        result = OutputFormatter.to_txt(sample_segments)
        
        lines = result.split("\n")
        assert len(lines) == 3
        
        # Check format
        assert "[00:00:01.000 --> 00:00:03.000] 这是第一句字幕" in result
        assert "[00:00:03.500 --> 00:00:05.000] 这是第二句字幕" in result

    def test_to_txt_empty(self):
        """Test TXT conversion with empty segments."""
        result = OutputFormatter.to_txt([])
        assert result == ""

    def test_to_markdown_basic(self, sample_result):
        """Test basic Markdown format conversion."""
        result = OutputFormatter.to_markdown(sample_result)
        
        # Check title
        assert "# Video: BV1xx411c7mD" in result
        
        # Check bullet points
        assert "- **00:00:01.000 - 00:00:03.000**: 这是第一句字幕" in result
        assert "- **00:00:03.500 - 00:00:05.000**: 这是第二句字幕" in result

    def test_validate_format_srt_valid(self, sample_segments):
        """Test SRT format validation with valid content."""
        content = OutputFormatter.to_srt(sample_segments)
        assert OutputFormatter.validate_format(content, "srt") is True

    def test_validate_format_srt_invalid(self):
        """Test SRT format validation with invalid content."""
        invalid_content = "This is not a valid SRT format"
        assert OutputFormatter.validate_format(invalid_content, "srt") is False

    def test_validate_format_json_valid(self, sample_result):
        """Test JSON format validation with valid content."""
        content = OutputFormatter.to_json(sample_result)
        assert OutputFormatter.validate_format(content, "json") is True

    def test_validate_format_json_invalid(self):
        """Test JSON format validation with invalid content."""
        invalid_content = '{"incomplete": "json"'
        assert OutputFormatter.validate_format(invalid_content, "json") is False

    def test_validate_format_json_missing_fields(self):
        """Test JSON format validation with missing required fields."""
        incomplete_json = json.dumps({"video_info": {}, "segments": []})
        assert OutputFormatter.validate_format(incomplete_json, "json") is False

    def test_validate_format_txt_valid(self, sample_segments):
        """Test TXT format validation with valid content."""
        content = OutputFormatter.to_txt(sample_segments)
        assert OutputFormatter.validate_format(content, "txt") is True

    def test_validate_format_txt_invalid(self):
        """Test TXT format validation with invalid content."""
        invalid_content = "This is plain text without timestamps"
        assert OutputFormatter.validate_format(invalid_content, "txt") is False

    def test_validate_format_markdown_valid(self, sample_result):
        """Test Markdown format validation with valid content."""
        content = OutputFormatter.to_markdown(sample_result)
        assert OutputFormatter.validate_format(content, "markdown") is True

    def test_validate_format_markdown_invalid(self):
        """Test Markdown format validation with invalid content."""
        invalid_content = "# Wrong format\nNo bullet points"
        assert OutputFormatter.validate_format(invalid_content, "markdown") is False

    def test_validate_format_empty_content(self):
        """Test format validation with empty content."""
        assert OutputFormatter.validate_format("", "srt") is True
        assert OutputFormatter.validate_format("", "json") is True
        assert OutputFormatter.validate_format("", "txt") is True
        assert OutputFormatter.validate_format("", "markdown") is True

    def test_validate_format_unknown_format(self):
        """Test format validation with unknown format type."""
        assert OutputFormatter.validate_format("content", "unknown") is False

    def test_srt_multiline_text(self):
        """Test SRT format with multiline text segments."""
        segments = [
            TextSegment(
                start_time=1.0,
                end_time=3.0,
                text="第一行\n第二行",
                confidence=1.0,
                source="subtitle"
            )
        ]
        
        result = OutputFormatter.to_srt(segments)
        assert "第一行\n第二行" in result

    def test_timestamp_precision(self):
        """Test timestamp precision in different formats."""
        segments = [
            TextSegment(
                start_time=1.123,
                end_time=2.987,
                text="测试精度",
                confidence=1.0,
                source="subtitle"
            )
        ]
        
        # SRT should have millisecond precision
        srt_result = OutputFormatter.to_srt(segments)
        assert "00:00:01,123" in srt_result
        assert "00:00:02,987" in srt_result
        
        # TXT should have millisecond precision
        txt_result = OutputFormatter.to_txt(segments)
        assert "00:00:01.123" in txt_result
        assert "00:00:02.987" in txt_result

    def test_json_metadata_preservation(self):
        """Test that JSON preserves all metadata."""
        video_info = VideoInfo(
            video_id="BV123",
            title="Test",
            duration=100,
            has_subtitle=False,
            url="https://test.com"
        )
        
        result = ExtractionResult(
            video_info=video_info,
            segments=[],
            method="asr",
            processing_time=5.5,
            metadata={"custom_field": "custom_value", "number": 42}
        )
        
        json_str = OutputFormatter.to_json(result)
        data = json.loads(json_str)
        
        assert data["metadata"]["custom_field"] == "custom_value"
        assert data["metadata"]["number"] == 42
        assert data["processing_time"] == 5.5
        assert data["method"] == "asr"
