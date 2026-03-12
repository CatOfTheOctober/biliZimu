"""Tests for standardized acquisition bundle outputs."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bilibili_extractor.core.config import Config
from bilibili_extractor.core.extractor import TextExtractor
from bilibili_extractor.core.models import ExtractionResult, TextSegment, VideoInfo
from bilibili_extractor.modules.acquisition_bundle import AcquisitionBundleBuilder


@pytest.fixture
def sample_result():
    return ExtractionResult(
        video_info=VideoInfo(
            video_id="BV1TEST123",
            title="测试视频",
            duration=120,
            has_subtitle=True,
            url="https://www.bilibili.com/video/BV1TEST123",
            description="desc",
            published_at="2026-03-12T00:00:00Z",
            uploader="Uploader",
            cid=1001,
            cover_url="https://example.com/cover.jpg",
        ),
        segments=[
            TextSegment(start_time=0.0, end_time=2.0, text="第一句", source="subtitle"),
            TextSegment(start_time=8.5, end_time=10.0, text="第二句", source="subtitle"),
        ],
        method="subtitle",
        processing_time=1.2,
        metadata={"subtitle_kind": "ai"},
    )


def test_acquisition_bundle_builder_exports_expected_files(tmp_path, sample_result):
    config = Config(output_dir=str(tmp_path / "output"))
    builder = AcquisitionBundleBuilder(config)

    raw_video = tmp_path / "video.mp4"
    raw_video.write_bytes(b"video")
    raw_audio = tmp_path / "audio.wav"
    raw_audio.write_bytes(b"audio")

    exported = builder.export(
        result=sample_result,
        output_root=tmp_path / "bundle_out",
        raw_video_path=raw_video,
        raw_audio_path=raw_audio,
        raw_subtitle_payload={"body": [{"from": 0, "to": 2, "content": "第一句"}]},
        raw_video_metadata={"bvid": "BV1TEST123", "title": "测试视频", "desc": "desc"},
        selected_track_metadata={
            "track_id": "selected_subtitle",
            "track_type": "subtitle",
            "source": "platform_ai_subtitle",
            "label": "AI字幕",
            "language": "ai-zh",
            "is_ai_generated": True,
        },
    )

    bundle_path = exported["bundle_path"]
    manifest_path = exported["manifest_path"]
    assert bundle_path.exists()
    assert manifest_path.exists()
    assert exported["selected_track_txt"].exists()
    assert exported["selected_track_srt"].exists()

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["video"]["bvid"] == "BV1TEST123"
    assert bundle["selected_track"] == "selected_subtitle"
    assert bundle["quality_flags"]["has_ai_subtitle"] is True
    assert bundle["quality_flags"]["missing_intervals"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert exported["bundle_dir"].name == "2026-03-12_测试视频_BV1TEST123"
    asset_types = {asset["asset_type"] for asset in manifest["assets"]}
    assert "video" in asset_types
    assert "audio" in asset_types
    assert "transcript_bundle" in asset_types


def test_text_extractor_writes_artifacts_for_subtitle_flow(tmp_path):
    config = Config(
        temp_dir=str(tmp_path / "temp"),
        output_dir=str(tmp_path / "output"),
        keep_temp_files=True,
    )
    extractor = TextExtractor(config)
    extractor.logger.close = Mock()
    extractor.resource_manager.cleanup = Mock()

    video_file = tmp_path / "temp" / "video.mp4"
    video_file.parent.mkdir(parents=True, exist_ok=True)
    video_file.write_bytes(b"video")
    audio_file = tmp_path / "temp" / "audio.wav"
    audio_file.write_bytes(b"audio")

    extractor.video_downloader = Mock()
    extractor.video_downloader.download.return_value = video_file
    extractor.audio_extractor = Mock()
    extractor.audio_extractor.extract.return_value = audio_file

    subtitle_fetcher = Mock(spec=["fetch_subtitle_details", "get_video_metadata"])
    subtitle_fetcher.get_video_metadata.return_value = {
        "bvid": "BV1TEST123",
        "title": "测试视频",
        "desc": "简介",
        "duration": 120,
        "cid": 1001,
        "owner_name": "Uploader",
        "page": 1,
        "pages": [],
        "pic": "https://example.com/cover.jpg",
        "pubdate": 1710201600,
    }
    subtitle_fetcher.fetch_subtitle_details.return_value = {
        "segments": [TextSegment(start_time=0.0, end_time=2.0, text="第一句", source="subtitle")],
        "video_info": subtitle_fetcher.get_video_metadata.return_value,
        "subtitle_result": {
            "raw_subtitle_data": {"body": [{"from": 0.0, "to": 2.0, "content": "第一句"}]},
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

    with patch("bilibili_extractor.core.extractor.URLValidator") as mock_validator:
        mock_validator.validate.return_value = True
        mock_validator.extract_video_id.return_value = "BV1TEST123"

        result = extractor.extract(
            "https://www.bilibili.com/video/BV1TEST123",
            artifact_dir=tmp_path / "artifacts",
        )

    assert Path(result.metadata["artifact_bundle_dir"]).exists()
    manifest_path = Path(result.metadata["artifact_manifest_path"])
    assert manifest_path.exists()
    bundle_path = Path(result.metadata["artifact_bundle_dir"]) / "derived" / "TranscriptBundle.json"
    assert bundle_path.exists()

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["video"]["title"] == "测试视频"
    assert bundle["tracks"][0]["source"] == "platform_ai_subtitle"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"


def test_acquisition_bundle_builder_exports_failure_manifest(tmp_path):
    config = Config(output_dir=str(tmp_path / "output"))
    builder = AcquisitionBundleBuilder(config)

    failed = builder.export_failure(
        output_root=tmp_path / "bundle_out",
        video_id="BV1FAIL123",
        title="失败视频",
        raw_video_metadata={"bvid": "BV1FAIL123", "title": "失败视频"},
        failure_stage="video_download",
        failure_reason="download failed",
    )

    manifest = json.loads(failed["manifest_path"].read_text(encoding="utf-8"))
    assert failed["bundle_dir"].name == "undated_失败视频_BV1FAIL123"
    assert manifest["status"] == "failed"
    assert manifest["failure_stage"] == "video_download"
    assert manifest["failure_reason"] == "download failed"
