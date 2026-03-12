"""Output formatting for extracted text."""

import json
import re
from typing import List
from datetime import datetime
from bilibili_extractor.core.models import (
    TextSegment,
    ExtractionResult,
    TranscriptBundle,
    TranscriptTrack,
    AssetManifest,
    AssetRecord,
)


class OutputFormatter:
    """Format extraction results to various output formats."""

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def to_srt(segments: List[TextSegment]) -> str:
        """Convert segments to SRT format.

        Args:
            segments: List of TextSegment objects

        Returns:
            SRT formatted string
        """
        if not segments:
            return ""
        
        srt_lines = []
        for idx, segment in enumerate(segments, start=1):
            # Sequence number
            srt_lines.append(str(idx))
            
            # Timestamp line
            start = OutputFormatter._format_srt_timestamp(segment.start_time)
            end = OutputFormatter._format_srt_timestamp(segment.end_time)
            srt_lines.append(f"{start} --> {end}")
            
            # Text content
            srt_lines.append(segment.text)
            
            # Empty line between entries
            srt_lines.append("")
        
        return "\n".join(srt_lines)

    @staticmethod
    def to_json(result: ExtractionResult) -> str:
        """Convert result to JSON format.

        Args:
            result: ExtractionResult object

        Returns:
            JSON formatted string
        """
        data = {
            "video_info": {
                "video_id": result.video_info.video_id,
                "title": result.video_info.title,
                "duration": result.video_info.duration,
                "has_subtitle": result.video_info.has_subtitle,
                "url": result.video_info.url
            },
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "text": seg.text,
                    "confidence": seg.confidence,
                    "source": seg.source
                }
                for seg in result.segments
            ],
            "method": result.method,
            "processing_time": result.processing_time,
            "metadata": result.metadata
        }
        
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_transcript_bundle(bundle: TranscriptBundle) -> str:
        """Convert a transcript bundle into its stable JSON representation."""
        data = {
            "schema_version": bundle.schema_version,
            "video": bundle.video,
            "tracks": [
                OutputFormatter._track_to_dict(track)
                for track in bundle.tracks
            ],
            "selected_track": bundle.selected_track,
            "quality_flags": bundle.quality_flags,
            "processing": bundle.processing,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_asset_manifest(manifest: AssetManifest) -> str:
        """Convert an asset manifest into JSON."""
        data = {
            "schema_version": manifest.schema_version,
            "bundle_id": manifest.bundle_id,
            "video_id": manifest.video_id,
            "created_at": manifest.created_at,
            "status": manifest.status,
            "failure_stage": manifest.failure_stage,
            "failure_reason": manifest.failure_reason,
            "assets": [
                OutputFormatter._asset_record_to_dict(asset)
                for asset in manifest.assets
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_txt(segments: List[TextSegment]) -> str:
        """Convert segments to plain text.

        Args:
            segments: List of TextSegment objects

        Returns:
            Plain text string with timestamps
        """
        if not segments:
            return ""
        
        lines = []
        for segment in segments:
            # Format timestamps
            start = f"{segment.start_time:.3f}".rstrip('0').rstrip('.')
            end = f"{segment.end_time:.3f}".rstrip('0').rstrip('.')
            
            # Format: [HH:MM:SS.mmm --> HH:MM:SS.mmm] text
            start_formatted = OutputFormatter._format_txt_timestamp(segment.start_time)
            end_formatted = OutputFormatter._format_txt_timestamp(segment.end_time)
            
            lines.append(f"[{start_formatted} --> {end_formatted}] {segment.text}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_txt_timestamp(seconds: float) -> str:
        """Format seconds to text timestamp format (HH:MM:SS.mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    @staticmethod
    def _track_to_dict(track: TranscriptTrack) -> dict:
        return {
            "track_id": track.track_id,
            "track_type": track.track_type,
            "source": track.source,
            "label": track.label,
            "language": track.language,
            "is_ai_generated": track.is_ai_generated,
            "segments": [
                {
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "text": segment.text,
                    "confidence": segment.confidence,
                    "source": segment.source,
                }
                for segment in track.segments
            ],
            "metadata": track.metadata,
        }

    @staticmethod
    def _asset_record_to_dict(asset: AssetRecord) -> dict:
        return {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type,
            "path": asset.path,
            "origin": asset.origin,
            "checksum": asset.checksum,
            "created_at": asset.created_at,
            "metadata": asset.metadata,
        }

    @staticmethod
    def to_markdown(result: ExtractionResult) -> str:
        """Convert result to Markdown format.

        Args:
            result: ExtractionResult object

        Returns:
            Markdown formatted string
        """
        lines = []
        
        # Title
        video_id = result.video_info.video_id
        lines.append(f"# Video: {video_id}")
        lines.append("")
        
        # Segments as bullet list
        for segment in result.segments:
            start_formatted = OutputFormatter._format_txt_timestamp(segment.start_time)
            end_formatted = OutputFormatter._format_txt_timestamp(segment.end_time)
            lines.append(f"- **{start_formatted} - {end_formatted}**: {segment.text}")
        
        return "\n".join(lines)

    @staticmethod
    def validate_format(content: str, format: str) -> bool:
        """Validate output format correctness.

        Args:
            content: Output content string
            format: Format type (srt/json/txt/markdown)

        Returns:
            True if valid, False otherwise
        """
        if not content:
            return True  # Empty content is valid
        
        try:
            if format == "srt":
                return OutputFormatter._validate_srt(content)
            elif format == "json":
                return OutputFormatter._validate_json(content)
            elif format == "txt":
                return OutputFormatter._validate_txt(content)
            elif format == "markdown":
                return OutputFormatter._validate_markdown(content)
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    def _validate_srt(content: str) -> bool:
        """Validate SRT format.
        
        Args:
            content: SRT content string
            
        Returns:
            True if valid SRT format
        """
        # Split into blocks
        blocks = content.strip().split("\n\n")
        
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                return False
            
            # Check sequence number
            if not lines[0].isdigit():
                return False
            
            # Check timestamp format
            timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$'
            if not re.match(timestamp_pattern, lines[1]):
                return False
            
            # Text should exist (lines[2] onwards) - allow empty text after stripping
            # At least one line of text must exist (even if empty)
        
        return True
    
    @staticmethod
    def _validate_json(content: str) -> bool:
        """Validate JSON format.
        
        Args:
            content: JSON content string
            
        Returns:
            True if valid JSON with required schema
        """
        try:
            data = json.loads(content)
            
            # Check required fields
            required_fields = ["video_info", "segments", "method", "processing_time"]
            if not all(field in data for field in required_fields):
                return False
            
            # Check video_info structure
            video_info_fields = ["video_id", "title", "duration", "has_subtitle", "url"]
            if not all(field in data["video_info"] for field in video_info_fields):
                return False
            
            # Check segments structure
            if not isinstance(data["segments"], list):
                return False
            
            for segment in data["segments"]:
                segment_fields = ["start_time", "end_time", "text", "confidence", "source"]
                if not all(field in segment for field in segment_fields):
                    return False
            
            return True
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
    
    @staticmethod
    def _validate_txt(content: str) -> bool:
        """Validate TXT format.
        
        Args:
            content: TXT content string
            
        Returns:
            True if valid TXT format with timestamps
        """
        lines = content.strip().split("\n")
        
        # Pattern: [HH:MM:SS.mmm --> HH:MM:SS.mmm] text (text can be empty or multiline)
        pattern = r'^\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\] '
        
        # Check first line of each segment
        i = 0
        while i < len(lines):
            if not re.match(pattern, lines[i]):
                return False
            # Skip any continuation lines (lines that don't start with timestamp)
            i += 1
            while i < len(lines) and not re.match(pattern, lines[i]):
                i += 1
        
        return True
    
    @staticmethod
    def _validate_markdown(content: str) -> bool:
        """Validate Markdown format.
        
        Args:
            content: Markdown content string
            
        Returns:
            True if valid Markdown format
        """
        lines = content.strip().split("\n")
        
        if not lines:
            return False
        
        # First line should be a title
        if not lines[0].startswith("# Video: "):
            return False
        
        # Check bullet points with timestamps (allow multiline text)
        pattern = r'^- \*\*\d{2}:\d{2}:\d{2}\.\d{3} - \d{2}:\d{2}:\d{2}\.\d{3}\*\*: '
        
        for line in lines[2:]:  # Skip title and empty line
            if line and not line.startswith("  ") and not re.match(pattern, line):
                return False
        
        return True
