"""Unit tests for TextExtractor."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bilibili_extractor.core.config import Config
from bilibili_extractor.core.exceptions import SubtitleNotFoundError
from bilibili_extractor.core.extractor import TextExtractor
from bilibili_extractor.core.models import ExtractionResult, TextSegment
from bilibili_extractor.modules.asr_engine import ASRError
from bilibili_extractor.modules.url_validator import URLValidationError
from bilibili_extractor.modules.video_downloader import DownloadError


class TestTextExtractor:
    @pytest.fixture
    def config(self, tmp_path):
        return Config(
            temp_dir=str(tmp_path / "temp"),
            output_dir=str(tmp_path / "output"),
            log_level="INFO",
            keep_temp_files=False,
        )

    @pytest.fixture
    def extractor(self, config):
        return TextExtractor(config)

    @pytest.fixture
    def video_metadata(self):
        return {
            "bvid": "BV1xx411c7mD",
            "title": "测试视频",
            "desc": "简介",
            "duration": 120,
            "cid": 12345,
            "owner_name": "UP主",
            "page": 1,
            "pages": [],
            "pic": "https://example.com/cover.jpg",
            "pubdate": 1710201600,
        }

    def test_init(self, extractor, config):
        assert extractor.config == config
        assert extractor.logger is not None
        assert extractor.resource_manager is not None
        assert extractor.subtitle_fetcher is not None

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_invalid_url(self, mock_validator, extractor):
        mock_validator.validate.return_value = False

        with pytest.raises(URLValidationError, match="Invalid URL"):
            extractor.extract("invalid_url")

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_with_api_subtitles_success(self, mock_validator, extractor, tmp_path, video_metadata):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        video_file = tmp_path / "source.mp4"
        video_file.write_bytes(b"video")
        extractor.video_downloader = Mock()
        extractor.video_downloader.download.return_value = video_file

        subtitle_fetcher = Mock(spec=["fetch_subtitle_details", "get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        subtitle_fetcher.fetch_subtitle_details.return_value = {
            "segments": [
                TextSegment(start_time=0.0, end_time=2.0, text="Hello", source="subtitle"),
                TextSegment(start_time=2.0, end_time=4.0, text="World", source="subtitle"),
            ],
            "video_info": video_metadata,
            "subtitle_result": {
                "raw_subtitle_data": {"body": [{"from": 0.0, "to": 2.0, "content": "Hello"}]}
            },
            "selected_track": {
                "track_id": "selected_subtitle",
                "track_type": "subtitle",
                "source": "platform_ai_subtitle",
                "label": "AI字幕",
                "language": "ai-zh",
                "is_ai_generated": True,
            },
        }
        extractor.subtitle_fetcher = subtitle_fetcher

        result = extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")

        assert isinstance(result, ExtractionResult)
        assert result.method == "subtitle"
        assert result.video_info.video_id == "BV1xx411c7mD"
        assert result.video_info.has_subtitle is True
        assert len(result.segments) == 2
        extractor.video_downloader.download.assert_called_once_with("BV1xx411c7mD", None)
        subtitle_fetcher.fetch_subtitle_details.assert_called_once()

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_subtitle_failure_raises_without_force_asr(self, mock_validator, extractor, tmp_path, video_metadata):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        video_file = tmp_path / "source.mp4"
        video_file.write_bytes(b"video")
        extractor.video_downloader = Mock()
        extractor.video_downloader.download.return_value = video_file

        subtitle_fetcher = Mock(spec=["fetch_subtitle_details", "get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        subtitle_fetcher.fetch_subtitle_details.side_effect = SubtitleNotFoundError("API获取字幕失败。")
        extractor.subtitle_fetcher = subtitle_fetcher

        with pytest.raises(SubtitleNotFoundError, match="API获取字幕失败"):
            extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")

        extractor.video_downloader.download.assert_called_once()

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_force_asr_success(self, mock_validator, extractor, tmp_path, video_metadata):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        video_file = tmp_path / "source.mp4"
        video_file.write_bytes(b"video")
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"audio")

        extractor.video_downloader = Mock()
        extractor.video_downloader.download.return_value = video_file
        extractor.audio_extractor = Mock()
        extractor.audio_extractor.extract.return_value = audio_file
        extractor.asr_engine = Mock()
        extractor.asr_engine.transcribe.return_value = [
            TextSegment(start_time=0.0, end_time=2.0, text="ASR result", source="asr")
        ]

        subtitle_fetcher = Mock(spec=["get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        extractor.subtitle_fetcher = subtitle_fetcher

        result = extractor.extract(
            "https://www.bilibili.com/video/BV1xx411c7mD",
            force_asr=True,
        )

        assert result.method == "asr"
        assert len(result.segments) == 1
        extractor.audio_extractor.extract.assert_called_once_with(video_file)
        extractor.asr_engine.transcribe.assert_called_once_with(audio_file, None)

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_cleanup_on_success(self, mock_validator, extractor, tmp_path, video_metadata):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        video_file = tmp_path / "source.mp4"
        video_file.write_bytes(b"video")
        extractor.video_downloader = Mock()
        extractor.video_downloader.download.return_value = video_file

        subtitle_fetcher = Mock(spec=["fetch_subtitle_details", "get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        subtitle_fetcher.fetch_subtitle_details.return_value = {
            "segments": [TextSegment(start_time=0.0, end_time=2.0, text="Test", source="subtitle")],
            "video_info": video_metadata,
            "subtitle_result": {},
            "selected_track": {"is_ai_generated": False},
        }
        extractor.subtitle_fetcher = subtitle_fetcher

        cleanup_mock = Mock()
        extractor.resource_manager.cleanup = cleanup_mock

        extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")

        cleanup_mock.assert_called_once()

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_cleanup_on_error(self, mock_validator, extractor, video_metadata):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        extractor.video_downloader = Mock()
        extractor.video_downloader.download.side_effect = RuntimeError("Test error")

        subtitle_fetcher = Mock(spec=["get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        extractor.subtitle_fetcher = subtitle_fetcher

        cleanup_mock = Mock()
        extractor.resource_manager.cleanup = cleanup_mock

        with pytest.raises(RuntimeError, match="Test error"):
            extractor.extract("https://www.bilibili.com/video/BV1xx411c7mD")

        cleanup_mock.assert_called_once()

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_writes_failure_manifest_when_subtitle_fetch_fails(
        self,
        mock_validator,
        extractor,
        tmp_path,
        video_metadata,
    ):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        video_file = tmp_path / "source.mp4"
        video_file.write_bytes(b"video")
        extractor.video_downloader = Mock()
        extractor.video_downloader.download.return_value = video_file

        subtitle_fetcher = Mock(spec=["fetch_subtitle_details", "get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        subtitle_fetcher.fetch_subtitle_details.side_effect = SubtitleNotFoundError("API获取字幕失败。")
        extractor.subtitle_fetcher = subtitle_fetcher

        with pytest.raises(SubtitleNotFoundError):
            extractor.extract(
                "https://www.bilibili.com/video/BV1xx411c7mD",
                artifact_dir=tmp_path / "artifacts",
            )

        manifest_path = (
            tmp_path / "artifacts" / "2024-03-12_测试视频_BV1xx411c7mD" / "manifest" / "AssetManifest.json"
        )
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        assert manifest["failure_stage"] == "subtitle_fetch"

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_writes_failure_manifest_when_video_download_fails(
        self,
        mock_validator,
        extractor,
        tmp_path,
        video_metadata,
    ):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        extractor.video_downloader = Mock()
        extractor.video_downloader.download.side_effect = DownloadError("下载失败")

        subtitle_fetcher = Mock(spec=["get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        extractor.subtitle_fetcher = subtitle_fetcher

        with pytest.raises(DownloadError):
            extractor.extract(
                "https://www.bilibili.com/video/BV1xx411c7mD",
                artifact_dir=tmp_path / "artifacts",
            )

        manifest_path = (
            tmp_path / "artifacts" / "2024-03-12_测试视频_BV1xx411c7mD" / "manifest" / "AssetManifest.json"
        )
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        assert manifest["failure_stage"] == "video_download"

    def test_extract_batch_all_success(self, extractor):
        mock_result1 = Mock()
        mock_result1.video_info.video_id = "BV1"
        mock_result2 = Mock()
        mock_result2.video_info.video_id = "BV2"

        extractor.extract = Mock(side_effect=[mock_result1, mock_result2])
        results = extractor.extract_batch(
            [
                "https://www.bilibili.com/video/BV1",
                "https://www.bilibili.com/video/BV2",
            ]
        )

        assert len(results) == 2
        assert extractor.extract.call_count == 2

    @patch("bilibili_extractor.core.extractor.URLValidator")
    def test_extract_force_asr_without_engine_raises(self, mock_validator, extractor, tmp_path, video_metadata):
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1xx411c7mD"

        video_file = tmp_path / "source.mp4"
        video_file.write_bytes(b"video")
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"audio")

        extractor.video_downloader = Mock()
        extractor.video_downloader.download.return_value = video_file
        extractor.audio_extractor = Mock()
        extractor.audio_extractor.extract.return_value = audio_file
        extractor.asr_engine = None

        subtitle_fetcher = Mock(spec=["get_video_metadata"])
        subtitle_fetcher.get_video_metadata.return_value = video_metadata
        extractor.subtitle_fetcher = subtitle_fetcher

        with pytest.raises(ASRError, match="No ASR engine available"):
            extractor.extract(
                "https://www.bilibili.com/video/BV1xx411c7mD",
                force_asr=True,
            )
