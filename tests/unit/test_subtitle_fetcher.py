"""Unit tests for SubtitleFetcher module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
from bilibili_extractor.modules.subtitle_fetcher import SubtitleFetcher, SubtitleNotFoundError
from bilibili_extractor.core.config import Config


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(temp_dir="./test_temp", cookie_file=None)


@pytest.fixture
def fetcher(config):
    """Create a SubtitleFetcher instance."""
    return SubtitleFetcher(config)


class TestSubtitleFetcher:
    """Test cases for SubtitleFetcher class."""

    def test_init(self, fetcher, config):
        """Test SubtitleFetcher initialization."""
        assert fetcher.config == config

    @patch('subprocess.run')
    @patch('tempfile.TemporaryDirectory')
    @patch('pathlib.Path.mkdir')
    def test_download_with_bbdown_no_subtitles(self, mock_mkdir, mock_tempdir, mock_run, fetcher):
        """Test download when no subtitles exist."""
        # Setup mock
        mock_tempdir.return_value.__enter__.return_value = "/tmp/test"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="不存在字幕",
            stderr=""
        )
        
        # Test
        with pytest.raises(SubtitleNotFoundError):
            fetcher._download_with_bbdown("BV1xx411c7mD")

    @patch('subprocess.run')
    @patch('tempfile.TemporaryDirectory')
    @patch('pathlib.Path.mkdir')
    def test_download_with_bbdown_command_failed(self, mock_mkdir, mock_tempdir, mock_run, fetcher):
        """Test download when BBDown command fails."""
        # Setup mock
        mock_tempdir.return_value.__enter__.return_value = "/tmp/test"
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: Network error"
        )
        
        # Test
        with pytest.raises(RuntimeError, match="BBDown command failed"):
            fetcher._download_with_bbdown("BV1xx411c7mD")

    @patch('subprocess.run')
    def test_download_with_bbdown_bbdown_not_found(self, mock_run, fetcher):
        """Test download when BBDown is not installed."""
        # Setup mock
        mock_run.side_effect = FileNotFoundError()
        
        # Test
        with pytest.raises(RuntimeError, match="BBDown not found"):
            fetcher._download_with_bbdown("BV1xx411c7mD")

    def test_find_subtitle_files(self, fetcher, tmp_path):
        """Test finding subtitle files in directory."""
        # Create test files
        (tmp_path / "subtitle.srt").touch()
        (tmp_path / "subtitle.json").touch()
        (tmp_path / "subtitle.xml").touch()
        (tmp_path / "video.mp4").touch()
        
        # Test
        files = fetcher._find_subtitle_files(tmp_path)
        
        # Verify
        assert len(files) == 3
        extensions = {f.suffix for f in files}
        assert extensions == {'.srt', '.json', '.xml'}

    def test_find_subtitle_files_empty(self, fetcher, tmp_path):
        """Test finding subtitle files in empty directory."""
        files = fetcher._find_subtitle_files(tmp_path)
        assert len(files) == 0

    @patch.object(SubtitleFetcher, 'download_subtitles')
    def test_check_subtitle_availability_true(self, mock_download, fetcher):
        """Test check_subtitle_availability when subtitles exist."""
        mock_download.return_value = [Path("subtitle.srt")]
        
        result = fetcher.check_subtitle_availability("BV1xx411c7mD")
        
        assert result is True
        mock_download.assert_called_once_with("BV1xx411c7mD")

    @patch.object(SubtitleFetcher, 'download_subtitles')
    def test_check_subtitle_availability_false(self, mock_download, fetcher):
        """Test check_subtitle_availability when subtitles don't exist."""
        mock_download.side_effect = SubtitleNotFoundError("No subtitles")
        
        result = fetcher.check_subtitle_availability("BV1xx411c7mD")
        
        assert result is False
        mock_download.assert_called_once_with("BV1xx411c7mD")

    def test_parse_subtitle_srt(self, fetcher):
        """Test parsing SRT format subtitle."""
        subtitle_path = Path("tests/fixtures/sample_subtitles/test_subtitle.srt")
        
        segments = fetcher.parse_subtitle(subtitle_path)
        
        assert len(segments) == 3
        
        # Check first segment
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 3.0
        assert segments[0].text == "这是第一句字幕"
        assert segments[0].confidence == 1.0
        assert segments[0].source == "subtitle"
        
        # Check second segment
        assert segments[1].start_time == 3.5
        assert segments[1].end_time == 5.0
        assert segments[1].text == "这是第二句字幕"
        
        # Check third segment (multi-line)
        assert segments[2].start_time == 5.2
        assert segments[2].end_time == 8.5
        assert "这是第三句字幕" in segments[2].text
        assert "包含多行文本" in segments[2].text

    def test_parse_subtitle_json(self, fetcher):
        """Test parsing Bilibili JSON format subtitle."""
        subtitle_path = Path("tests/fixtures/sample_subtitles/test_subtitle.json")
        
        segments = fetcher.parse_subtitle(subtitle_path)
        
        assert len(segments) == 3
        
        # Check first segment
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 3.0
        assert segments[0].text == "这是第一句字幕"
        assert segments[0].confidence == 1.0
        assert segments[0].source == "subtitle"
        
        # Check second segment
        assert segments[1].start_time == 3.5
        assert segments[1].end_time == 5.0
        assert segments[1].text == "这是第二句字幕"
        
        # Check third segment
        assert segments[2].start_time == 5.2
        assert segments[2].end_time == 8.5
        assert segments[2].text == "这是第三句字幕"

    def test_parse_subtitle_xml(self, fetcher):
        """Test parsing XML format subtitle."""
        subtitle_path = Path("tests/fixtures/sample_subtitles/test_subtitle.xml")
        
        segments = fetcher.parse_subtitle(subtitle_path)
        
        assert len(segments) == 3
        
        # Check first segment
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 3.0
        assert segments[0].text == "这是第一句字幕"
        assert segments[0].confidence == 1.0
        assert segments[0].source == "subtitle"
        
        # Check second segment
        assert segments[1].start_time == 3.5
        assert segments[1].end_time == 5.0
        assert segments[1].text == "这是第二句字幕"
        
        # Check third segment
        assert segments[2].start_time == 5.2
        assert segments[2].end_time == 8.5
        assert segments[2].text == "这是第三句字幕"

    def test_parse_subtitle_file_not_found(self, fetcher):
        """Test parsing non-existent subtitle file."""
        subtitle_path = Path("tests/fixtures/sample_subtitles/nonexistent.srt")
        
        with pytest.raises(ValueError, match="Subtitle file not found"):
            fetcher.parse_subtitle(subtitle_path)

    def test_parse_subtitle_unsupported_format(self, fetcher, tmp_path):
        """Test parsing unsupported subtitle format."""
        subtitle_path = tmp_path / "subtitle.txt"
        subtitle_path.write_text("Some text")
        
        with pytest.raises(ValueError, match="Unsupported subtitle format"):
            fetcher.parse_subtitle(subtitle_path)

    def test_parse_subtitle_timestamps_sorted(self, fetcher):
        """Test that parsed segments are sorted by start_time."""
        # Create a subtitle file with out-of-order timestamps
        subtitle_content = """1
00:00:05,000 --> 00:00:07,000
Third segment

2
00:00:01,000 --> 00:00:03,000
First segment

3
00:00:03,000 --> 00:00:05,000
Second segment
"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(subtitle_content)
            temp_path = Path(f.name)
        
        try:
            segments = fetcher.parse_subtitle(temp_path)
            
            # Verify segments are sorted
            assert len(segments) == 3
            assert segments[0].text == "First segment"
            assert segments[1].text == "Second segment"
            assert segments[2].text == "Third segment"
            
            # Verify timestamps are monotonic
            for i in range(len(segments) - 1):
                assert segments[i].start_time <= segments[i + 1].start_time
        finally:
            temp_path.unlink()

    def test_select_chinese_subtitle_single_file(self, fetcher):
        """Test selecting Chinese subtitle when only one file exists."""
        files = [Path("tests/fixtures/sample_subtitles/test_subtitle.srt")]
        
        selected = fetcher._select_chinese_subtitle(files)
        
        assert selected == files[0]

    def test_select_chinese_subtitle_zh_cn(self, fetcher):
        """Test selecting Chinese subtitle with zh-CN pattern."""
        files = [
            Path("tests/fixtures/sample_subtitles/test_subtitle_en.srt"),
            Path("tests/fixtures/sample_subtitles/test_subtitle_zh-CN.srt")
        ]
        
        selected = fetcher._select_chinese_subtitle(files)
        
        assert "zh-CN" in selected.name or "zh_CN" in selected.name

    def test_select_chinese_subtitle_no_chinese(self, fetcher):
        """Test selecting subtitle when no Chinese subtitle exists."""
        files = [
            Path("tests/fixtures/sample_subtitles/test_subtitle_en.srt"),
            Path("tests/fixtures/sample_subtitles/test_subtitle.srt")
        ]
        
        selected = fetcher._select_chinese_subtitle(files)
        
        # Should return the first file
        assert selected == files[0]

    def test_select_chinese_subtitle_empty_list(self, fetcher):
        """Test selecting Chinese subtitle with empty list."""
        with pytest.raises(ValueError, match="No subtitle files provided"):
            fetcher._select_chinese_subtitle([])

    def test_parse_srt_empty_blocks(self, fetcher, tmp_path):
        """Test parsing SRT with empty blocks."""
        subtitle_path = tmp_path / "empty.srt"
        subtitle_path.write_text("""1
00:00:01,000 --> 00:00:03,000
Valid subtitle


2
00:00:05,000 --> 00:00:07,000

""", encoding='utf-8')
        
        segments = fetcher.parse_subtitle(subtitle_path)
        
        # Should only parse the valid subtitle
        assert len(segments) == 1
        assert segments[0].text == "Valid subtitle"

    def test_parse_json_empty_body(self, fetcher, tmp_path):
        """Test parsing JSON with empty body."""
        subtitle_path = tmp_path / "empty.json"
        subtitle_path.write_text('{"body": []}', encoding='utf-8')
        
        segments = fetcher.parse_subtitle(subtitle_path)
        
        assert len(segments) == 0

    def test_parse_xml_no_segments(self, fetcher, tmp_path):
        """Test parsing XML with no subtitle segments."""
        subtitle_path = tmp_path / "empty.xml"
        subtitle_path.write_text('<?xml version="1.0"?><subtitle><body></body></subtitle>', encoding='utf-8')
        
        segments = fetcher.parse_subtitle(subtitle_path)
        
        assert len(segments) == 0
