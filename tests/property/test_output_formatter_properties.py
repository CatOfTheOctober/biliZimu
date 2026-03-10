"""Property-based tests for OutputFormatter.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

This module tests the correctness properties of output formatting:
- Property 20: SRT输出应能被标准SRT解析器解析
- Property 21: JSON输出应符合定义的schema
- Property 22: 格式转换应保持时间戳信息不丢失
- Property 23: 重新解析输出文件应得到等价的数据结构
"""

import json
import re

# Try to import hypothesis for property-based tests
try:
    from hypothesis import given, strategies as st, assume, settings, HealthCheck
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Create dummy decorators if hypothesis is not available
    def given(*args, **kwargs):
        return lambda f: f
    def settings(*args, **kwargs):
        return lambda f: f
    def assume(*args, **kwargs):
        pass
    class st:
        @staticmethod
        def composite(f):
            def wrapper(*args, **kwargs):
                return []
            return wrapper
        @staticmethod
        def floats(*args, **kwargs):
            return []
        @staticmethod
        def text(*args, **kwargs):
            return []
        @staticmethod
        def lists(*args, **kwargs):
            return []
    class HealthCheck:
        too_slow = None

from bilibili_extractor.modules.output_formatter import OutputFormatter
from bilibili_extractor.core.models import TextSegment, ExtractionResult, VideoInfo


# Strategy for generating valid timestamps
@st.composite
def timestamp_pair(draw):
    """Generate a valid (start_time, end_time) pair."""
    start = draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False))
    duration = draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False))
    end = start + duration
    return (start, end)


# Strategy for generating TextSegments
@st.composite
def text_segment(draw):
    """Generate a valid TextSegment."""
    start, end = draw(timestamp_pair())
    # Generate simple alphanumeric text to avoid whitespace edge cases
    text = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Lo'), min_codepoint=0x20, max_codepoint=0x7E) | st.sampled_from('你好世界测试')))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    source = draw(st.sampled_from(["subtitle", "asr", "ocr"]))
    
    return TextSegment(
        start_time=start,
        end_time=end,
        text=text,
        confidence=confidence,
        source=source
    )


# Strategy for generating list of TextSegments with monotonic timestamps
@st.composite
def text_segments_list(draw):
    """Generate a list of TextSegments with monotonically increasing timestamps."""
    segments = draw(st.lists(text_segment(), min_size=0, max_size=10))
    
    # Sort by start_time to ensure monotonic timestamps
    segments.sort(key=lambda s: s.start_time)
    
    return segments


# Strategy for generating VideoInfo
@st.composite
def video_info(draw):
    """Generate a valid VideoInfo."""
    video_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    title = draw(st.text(min_size=1, max_size=100))
    duration = draw(st.integers(min_value=1, max_value=7200))
    has_subtitle = draw(st.booleans())
    url = f"https://www.bilibili.com/video/{video_id}"
    
    return VideoInfo(
        video_id=video_id,
        title=title,
        duration=duration,
        has_subtitle=has_subtitle,
        url=url
    )


# Strategy for generating ExtractionResult
@st.composite
def extraction_result(draw):
    """Generate a valid ExtractionResult."""
    v_info = draw(video_info())
    segments = draw(text_segments_list())
    method = draw(st.sampled_from(["subtitle", "asr", "hybrid"]))
    processing_time = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    
    return ExtractionResult(
        video_info=v_info,
        segments=segments,
        method=method,
        processing_time=processing_time,
        metadata={}
    )


class TestOutputFormatterProperties:
    """Property-based tests for OutputFormatter."""

    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    @given(text_segments_list())
    def test_property_20_srt_parseable(self, segments):
        """Property 20: SRT输出应能被标准SRT解析器解析.
        
        **Validates: Requirements 7.1, 7.2, 7.3, 7.7**
        """
        # Generate SRT output
        srt_output = OutputFormatter.to_srt(segments)
        
        # Property: SRT output should be valid and parseable
        if segments:
            # Should validate as correct SRT format
            assert OutputFormatter.validate_format(srt_output, "srt")
            
            # Should be parseable by regex
            blocks = srt_output.strip().split("\n\n")
            assert len(blocks) == len(segments)
            
            for block in blocks:
                lines = block.strip().split("\n")
                # Each block should have at least 3 lines: number, timestamp, text
                assert len(lines) >= 3
                
                # First line should be a number
                assert lines[0].isdigit()
                
                # Second line should be timestamp
                timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$'
                assert re.match(timestamp_pattern, lines[1])
        else:
            # Empty segments should produce empty output
            assert srt_output == ""

    @settings(max_examples=50)
    @given(extraction_result())
    def test_property_21_json_schema_valid(self, result):
        """Property 21: JSON输出应符合定义的schema.
        
        **Validates: Requirements 7.1, 7.2, 7.3, 7.6, 7.7**
        """
        # Generate JSON output
        json_output = OutputFormatter.to_json(result)
        
        # Property: JSON should be valid and conform to schema
        assert OutputFormatter.validate_format(json_output, "json")
        
        # Parse and verify structure
        data = json.loads(json_output)
        
        # Required top-level fields
        assert "video_info" in data
        assert "segments" in data
        assert "method" in data
        assert "processing_time" in data
        assert "metadata" in data
        
        # Video info fields
        assert "video_id" in data["video_info"]
        assert "title" in data["video_info"]
        assert "duration" in data["video_info"]
        assert "has_subtitle" in data["video_info"]
        assert "url" in data["video_info"]
        
        # Segments structure
        assert isinstance(data["segments"], list)
        assert len(data["segments"]) == len(result.segments)
        
        for segment_data in data["segments"]:
            assert "start_time" in segment_data
            assert "end_time" in segment_data
            assert "text" in segment_data
            assert "confidence" in segment_data
            assert "source" in segment_data

    @settings(max_examples=50)
    @given(text_segments_list())
    def test_property_22_timestamp_preservation_srt(self, segments):
        """Property 22: 格式转换应保持时间戳信息不丢失 (SRT format).
        
        **Validates: Requirements 7.2, 7.3**
        """
        assume(len(segments) > 0)
        
        # Generate SRT output
        srt_output = OutputFormatter.to_srt(segments)
        
        # Property: All timestamps should be preserved in output
        for segment in segments:
            # Extract hours, minutes, seconds, milliseconds
            start_h = int(segment.start_time // 3600)
            start_m = int((segment.start_time % 3600) // 60)
            start_s = int(segment.start_time % 60)
            start_ms = int((segment.start_time % 1) * 1000)
            
            end_h = int(segment.end_time // 3600)
            end_m = int((segment.end_time % 3600) // 60)
            end_s = int(segment.end_time % 60)
            end_ms = int((segment.end_time % 1) * 1000)
            
            # Build expected timestamp string
            start_str = f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d}"
            end_str = f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}"
            
            # Verify timestamp appears in output
            assert start_str in srt_output
            assert end_str in srt_output

    @settings(max_examples=50)
    @given(text_segments_list())
    def test_property_22_timestamp_preservation_txt(self, segments):
        """Property 22: 格式转换应保持时间戳信息不丢失 (TXT format).
        
        **Validates: Requirements 7.2, 7.3**
        """
        assume(len(segments) > 0)
        
        # Generate TXT output
        txt_output = OutputFormatter.to_txt(segments)
        
        # Property: All timestamps should be preserved in output
        for segment in segments:
            # Extract hours, minutes, seconds
            start_h = int(segment.start_time // 3600)
            start_m = int((segment.start_time % 3600) // 60)
            start_s = segment.start_time % 60
            
            end_h = int(segment.end_time // 3600)
            end_m = int((segment.end_time % 3600) // 60)
            end_s = segment.end_time % 60
            
            # Build expected timestamp string (with millisecond precision)
            start_str = f"{start_h:02d}:{start_m:02d}:{start_s:06.3f}"
            end_str = f"{end_h:02d}:{end_m:02d}:{end_s:06.3f}"
            
            # Verify timestamp appears in output
            assert start_str in txt_output
            assert end_str in txt_output

    @settings(max_examples=50)
    @given(extraction_result())
    def test_property_23_json_round_trip(self, result):
        """Property 23: 重新解析输出文件应得到等价的数据结构 (JSON).
        
        **Validates: Requirements 7.1, 7.2, 7.3, 7.6, 7.7**
        """
        # Generate JSON output
        json_output = OutputFormatter.to_json(result)
        
        # Parse back
        parsed_data = json.loads(json_output)
        
        # Property: Parsed data should be equivalent to original
        assert parsed_data["video_info"]["video_id"] == result.video_info.video_id
        assert parsed_data["video_info"]["title"] == result.video_info.title
        assert parsed_data["video_info"]["duration"] == result.video_info.duration
        assert parsed_data["video_info"]["has_subtitle"] == result.video_info.has_subtitle
        assert parsed_data["video_info"]["url"] == result.video_info.url
        
        assert parsed_data["method"] == result.method
        assert parsed_data["processing_time"] == result.processing_time
        
        assert len(parsed_data["segments"]) == len(result.segments)
        
        for parsed_seg, orig_seg in zip(parsed_data["segments"], result.segments):
            assert parsed_seg["start_time"] == orig_seg.start_time
            assert parsed_seg["end_time"] == orig_seg.end_time
            assert parsed_seg["text"] == orig_seg.text
            assert parsed_seg["confidence"] == orig_seg.confidence
            assert parsed_seg["source"] == orig_seg.source

    @settings(max_examples=50)
    @given(text_segments_list())
    def test_property_23_srt_structure_round_trip(self, segments):
        """Property 23: 重新解析输出文件应得到等价的数据结构 (SRT structure).
        
        **Validates: Requirements 7.1, 7.2, 7.3, 7.7**
        """
        assume(len(segments) > 0)
        
        # Generate SRT output
        srt_output = OutputFormatter.to_srt(segments)
        
        # Parse SRT back into structure
        blocks = srt_output.strip().split("\n\n")
        
        # Property: Number of blocks should match number of segments
        assert len(blocks) == len(segments)
        
        # Property: Each block should have correct structure
        for idx, (block, original_seg) in enumerate(zip(blocks, segments), start=1):
            lines = block.strip().split("\n")
            
            # Sequence number should match
            assert int(lines[0]) == idx
            
            # Timestamp line exists
            assert " --> " in lines[1]
            
            # Text content should be preserved (may span multiple lines)
            text_content = "\n".join(lines[2:])
            assert text_content == original_seg.text

    @settings(max_examples=50)
    @given(text_segments_list())
    def test_all_formats_preserve_segment_count(self, segments):
        """Property: All formats should preserve the number of segments.
        
        **Validates: Requirements 7.1, 7.3**
        """
        # Generate outputs
        srt_output = OutputFormatter.to_srt(segments)
        txt_output = OutputFormatter.to_txt(segments)
        
        if segments:
            # Count segments in each format
            srt_blocks = len(srt_output.strip().split("\n\n"))
            txt_lines = len([line for line in txt_output.strip().split("\n") if line.startswith("[")])
            
            # Property: Segment count should be preserved
            assert srt_blocks == len(segments)
            assert txt_lines == len(segments)
        else:
            # Empty segments should produce empty output
            assert srt_output == ""
            assert txt_output == ""

    @settings(max_examples=50)
    @given(extraction_result())
    def test_markdown_preserves_video_id(self, result):
        """Property: Markdown format should preserve video ID in title.
        
        **Validates: Requirements 7.1, 7.6**
        """
        # Generate Markdown output
        md_output = OutputFormatter.to_markdown(result)
        
        # Property: Video ID should appear in title
        assert f"# Video: {result.video_info.video_id}" in md_output
        
        # Property: Should validate as correct markdown
        assert OutputFormatter.validate_format(md_output, "markdown")

    @settings(max_examples=50)
    @given(text_segments_list())
    def test_format_validation_consistency(self, segments):
        """Property: Generated output should always pass its own validation.
        
        **Validates: Requirements 7.7**
        """
        # Generate outputs
        srt_output = OutputFormatter.to_srt(segments)
        txt_output = OutputFormatter.to_txt(segments)
        
        # Property: Generated output should validate correctly
        assert OutputFormatter.validate_format(srt_output, "srt")
        assert OutputFormatter.validate_format(txt_output, "txt")

    @settings(max_examples=50)
    @given(extraction_result())
    def test_json_validation_consistency(self, result):
        """Property: Generated JSON should always pass validation.
        
        **Validates: Requirements 7.7**
        """
        # Generate JSON output
        json_output = OutputFormatter.to_json(result)
        
        # Property: Generated JSON should validate correctly
        assert OutputFormatter.validate_format(json_output, "json")
