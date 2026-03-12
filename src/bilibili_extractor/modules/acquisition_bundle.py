"""Archive acquisition outputs into replayable bundle artifacts."""

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bilibili_extractor import __version__
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import (
    AssetManifest,
    AssetRecord,
    ExtractionResult,
    TextSegment,
    TranscriptBundle,
    TranscriptTrack,
)
from bilibili_extractor.modules.output_formatter import OutputFormatter


class AcquisitionBundleBuilder:
    """Builds stable acquisition artifacts for downstream processing."""

    TRANSCRIPT_SCHEMA_VERSION = "1.0"
    MANIFEST_SCHEMA_VERSION = "1.0"

    def __init__(self, config: Config):
        self.config = config

    def export(
        self,
        result: ExtractionResult,
        output_root: Path,
        raw_video_path: Optional[Path] = None,
        raw_audio_path: Optional[Path] = None,
        raw_subtitle_payload: Optional[Dict[str, Any]] = None,
        raw_video_metadata: Optional[Dict[str, Any]] = None,
        selected_track_metadata: Optional[Dict[str, Any]] = None,
        status: str = "completed",
        failure_stage: Optional[str] = None,
        failure_reason: str = "",
    ) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat() + "Z"
        bundle_dir = self._make_bundle_dir(
            output_root=output_root,
            title=result.video_info.title,
            video_id=result.video_info.video_id,
            published_at=result.video_info.published_at,
            raw_video_metadata=raw_video_metadata,
        )
        raw_dir = bundle_dir / "raw"
        derived_dir = bundle_dir / "derived"
        manifest_dir = bundle_dir / "manifest"
        for directory in (raw_dir, derived_dir, manifest_dir):
            directory.mkdir(parents=True, exist_ok=True)

        assets = []

        if raw_video_path and raw_video_path.exists():
            video_copy = raw_dir / ("source_video" + raw_video_path.suffix)
            shutil.copy2(str(raw_video_path), str(video_copy))
            assets.append(self._record_asset("raw_video", "video", video_copy, "downloaded_video", timestamp))

        if raw_audio_path and raw_audio_path.exists():
            audio_copy = derived_dir / ("source_audio" + raw_audio_path.suffix)
            shutil.copy2(str(raw_audio_path), str(audio_copy))
            assets.append(self._record_asset("derived_audio", "audio", audio_copy, "extracted_audio", timestamp))

        if raw_subtitle_payload is not None:
            subtitle_json_path = raw_dir / "subtitle_payload.json"
            subtitle_json_path.write_text(
                json.dumps(raw_subtitle_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            assets.append(
                self._record_asset(
                    "raw_subtitle_payload",
                    "subtitle_payload",
                    subtitle_json_path,
                    "platform_api",
                    timestamp,
                )
            )

        if raw_video_metadata is not None:
            metadata_path = raw_dir / "video_metadata.json"
            metadata_path.write_text(
                json.dumps(raw_video_metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            assets.append(
                self._record_asset(
                    "raw_video_metadata",
                    "video_metadata",
                    metadata_path,
                    "platform_api",
                    timestamp,
                )
            )

        track = self._build_selected_track(result, selected_track_metadata)
        bundle = TranscriptBundle(
            schema_version=self.TRANSCRIPT_SCHEMA_VERSION,
            video=self._build_video_payload(result, raw_video_metadata),
            tracks=[track],
            selected_track=track.track_id,
            quality_flags=self._build_quality_flags(result.segments, track, result.video_info.duration),
            processing=self._build_processing_payload(result),
        )

        bundle_path = derived_dir / "TranscriptBundle.json"
        bundle_path.write_text(OutputFormatter.to_transcript_bundle(bundle), encoding="utf-8")
        assets.append(
            self._record_asset(
                "transcript_bundle",
                "transcript_bundle",
                bundle_path,
                "acquisition_pipeline",
                timestamp,
            )
        )

        txt_path = derived_dir / "selected_track.txt"
        txt_path.write_text(OutputFormatter.to_txt(result.segments), encoding="utf-8")
        assets.append(
            self._record_asset("selected_track_txt", "transcript_txt", txt_path, track.source, timestamp)
        )

        srt_path = derived_dir / "selected_track.srt"
        srt_path.write_text(OutputFormatter.to_srt(result.segments), encoding="utf-8")
        assets.append(
            self._record_asset("selected_track_srt", "transcript_srt", srt_path, track.source, timestamp)
        )

        manifest = AssetManifest(
            schema_version=self.MANIFEST_SCHEMA_VERSION,
            bundle_id=bundle_dir.name,
            video_id=result.video_info.video_id,
            created_at=timestamp,
            status=status,
            failure_stage=failure_stage,
            failure_reason=failure_reason,
            assets=assets,
        )
        manifest_path = manifest_dir / "AssetManifest.json"
        manifest_path.write_text(OutputFormatter.to_asset_manifest(manifest), encoding="utf-8")

        return {
            "bundle_dir": bundle_dir,
            "bundle_path": bundle_path,
            "manifest_path": manifest_path,
            "selected_track_txt": txt_path,
            "selected_track_srt": srt_path,
        }

    def export_failure(
        self,
        output_root: Path,
        video_id: str,
        title: str = "",
        raw_video_path: Optional[Path] = None,
        raw_subtitle_payload: Optional[Dict[str, Any]] = None,
        raw_video_metadata: Optional[Dict[str, Any]] = None,
        failure_stage: str = "unknown",
        failure_reason: str = "",
    ) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat() + "Z"
        bundle_dir = self._make_bundle_dir(
            output_root=output_root,
            title=title,
            video_id=video_id,
            raw_video_metadata=raw_video_metadata,
        )
        raw_dir = bundle_dir / "raw"
        manifest_dir = bundle_dir / "manifest"
        for directory in (raw_dir, manifest_dir):
            directory.mkdir(parents=True, exist_ok=True)

        assets = []

        if raw_video_path and raw_video_path.exists():
            video_copy = raw_dir / ("source_video" + raw_video_path.suffix)
            shutil.copy2(str(raw_video_path), str(video_copy))
            assets.append(self._record_asset("raw_video", "video", video_copy, "downloaded_video", timestamp))

        if raw_subtitle_payload is not None:
            subtitle_json_path = raw_dir / "subtitle_payload.json"
            subtitle_json_path.write_text(
                json.dumps(raw_subtitle_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            assets.append(
                self._record_asset(
                    "raw_subtitle_payload",
                    "subtitle_payload",
                    subtitle_json_path,
                    "platform_api",
                    timestamp,
                )
            )

        if raw_video_metadata is not None:
            metadata_path = raw_dir / "video_metadata.json"
            metadata_path.write_text(
                json.dumps(raw_video_metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            assets.append(
                self._record_asset(
                    "raw_video_metadata",
                    "video_metadata",
                    metadata_path,
                    "platform_api",
                    timestamp,
                )
            )

        manifest = AssetManifest(
            schema_version=self.MANIFEST_SCHEMA_VERSION,
            bundle_id=bundle_dir.name,
            video_id=video_id,
            created_at=timestamp,
            status="failed",
            failure_stage=failure_stage,
            failure_reason=failure_reason,
            assets=assets,
        )
        manifest_path = manifest_dir / "AssetManifest.json"
        manifest_path.write_text(OutputFormatter.to_asset_manifest(manifest), encoding="utf-8")

        return {
            "bundle_dir": bundle_dir,
            "manifest_path": manifest_path,
        }

    def _make_bundle_dir(
        self,
        output_root: Path,
        title: str,
        video_id: str,
        published_at: Optional[str] = None,
        raw_video_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        date_prefix = self._resolve_date_prefix(published_at, raw_video_metadata)
        safe_title = re.sub(r'[<>:"/\\|?*]+', "_", title or video_id).strip("._ ")
        safe_title = safe_title or video_id
        return output_root / f"{date_prefix}_{safe_title}_{video_id}"

    def _resolve_date_prefix(
        self,
        published_at: Optional[str],
        raw_video_metadata: Optional[Dict[str, Any]],
    ) -> str:
        if published_at:
            normalized = self._normalize_date_string(published_at)
            if normalized:
                return normalized

        metadata = raw_video_metadata or {}
        pubdate = metadata.get("pubdate")
        if pubdate is not None:
            try:
                return datetime.utcfromtimestamp(int(pubdate)).strftime("%Y-%m-%d")
            except Exception:
                normalized = self._normalize_date_string(str(pubdate))
                if normalized:
                    return normalized

        return "undated"

    def _normalize_date_string(self, value: str) -> Optional[str]:
        value = value.strip()
        if not value:
            return None

        direct_match = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
        if direct_match:
            return direct_match.group(1)

        compact_match = re.match(r"^(\d{4})(\d{2})(\d{2})$", value)
        if compact_match:
            return f"{compact_match.group(1)}-{compact_match.group(2)}-{compact_match.group(3)}"

        for pattern in ("%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(value, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def _record_asset(
        self,
        asset_id: str,
        asset_type: str,
        path: Path,
        origin: str,
        created_at: str,
    ) -> AssetRecord:
        return AssetRecord(
            asset_id=asset_id,
            asset_type=asset_type,
            path=str(path),
            origin=origin,
            checksum=self._checksum(path),
            created_at=created_at,
        )

    def _checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _build_selected_track(
        self,
        result: ExtractionResult,
        selected_track_metadata: Optional[Dict[str, Any]],
    ) -> TranscriptTrack:
        metadata = dict(selected_track_metadata or {})
        source = metadata.get("source") or self._infer_track_source(result)
        label = metadata.get("label") or result.method
        track_type = metadata.get("track_type") or ("asr" if result.method == "asr" else "subtitle")
        language = metadata.get("language")
        is_ai_generated = bool(metadata.get("is_ai_generated", False))
        track_id = metadata.get("track_id") or "selected_%s" % track_type

        return TranscriptTrack(
            track_id=track_id,
            track_type=track_type,
            source=source,
            label=label,
            language=language,
            is_ai_generated=is_ai_generated,
            segments=list(result.segments),
            metadata=metadata,
        )

    def _infer_track_source(self, result: ExtractionResult) -> str:
        if result.method == "asr":
            return "asr"
        if result.metadata.get("subtitle_kind") == "ai":
            return "platform_ai_subtitle"
        return "platform_subtitle"

    def _build_video_payload(
        self,
        result: ExtractionResult,
        raw_video_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        info = result.video_info
        metadata = raw_video_metadata or {}
        return {
            "bvid": info.video_id,
            "title": info.title,
            "description": info.description or metadata.get("desc", ""),
            "published_at": info.published_at,
            "uploader": info.uploader or metadata.get("owner_name", ""),
            "url": info.url,
            "cid": info.cid,
            "cover_url": info.cover_url or metadata.get("pic", ""),
            "duration": info.duration,
            "page": info.page,
            "pages": info.pages,
        }

    def _build_processing_payload(self, result: ExtractionResult) -> Dict[str, Any]:
        return {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "tool_version": __version__,
            "extraction_method": result.method,
            "processing_time_seconds": result.processing_time,
            "parameters": {
                "asr_engine": self.config.asr_engine,
                "video_quality": self.config.video_quality,
                "output_format": self.config.output_format,
            },
            "metadata": result.metadata,
        }

    def _build_quality_flags(
        self,
        segments: List[TextSegment],
        track: TranscriptTrack,
        duration: int,
    ) -> Dict[str, Any]:
        missing_intervals = []
        anomalous_intervals = []
        sorted_segments = sorted(segments, key=lambda item: item.start_time)
        previous_end = 0.0
        for segment in sorted_segments:
            if segment.end_time < segment.start_time:
                anomalous_intervals.append(
                    {
                        "start": segment.start_time,
                        "end": segment.end_time,
                        "reason": "negative_duration",
                    }
                )
            if segment.start_time > previous_end + 5.0:
                missing_intervals.append(
                    {
                        "start": round(previous_end, 3),
                        "end": round(segment.start_time, 3),
                    }
                )
            if segment.start_time < previous_end:
                anomalous_intervals.append(
                    {
                        "start": segment.start_time,
                        "end": previous_end,
                        "reason": "overlap",
                    }
                )
            previous_end = max(previous_end, segment.end_time)

        if duration and previous_end and duration > previous_end + 5.0:
            missing_intervals.append(
                {
                    "start": round(previous_end, 3),
                    "end": round(float(duration), 3),
                }
            )

        completeness_status = "complete"
        if not sorted_segments:
            completeness_status = "empty"
        elif missing_intervals or anomalous_intervals:
            completeness_status = "partial"

        return {
            "has_official_subtitle": track.track_type == "subtitle" and not track.is_ai_generated,
            "has_ai_subtitle": track.is_ai_generated,
            "has_asr": track.track_type == "asr",
            "missing_intervals": missing_intervals,
            "anomalous_intervals": anomalous_intervals,
            "text_completeness_status": completeness_status,
            "selected_track_source": track.source,
        }
