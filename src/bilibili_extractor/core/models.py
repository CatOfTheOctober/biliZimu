"""Data models for bilibili-extractor.

This module defines the core data structures used throughout the extraction process.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class VideoInfo:
    """Information about a Bilibili video.
    
    Attributes:
        video_id: BV号或av号，视频的唯一标识符
        title: 视频标题
        duration: 视频时长（秒）
        has_subtitle: 是否存在官方字幕
        url: 视频的完整URL地址
    """

    video_id: str
    title: str
    duration: int  # 秒
    has_subtitle: bool
    url: str
    description: str = ""
    published_at: Optional[str] = None
    uploader: str = ""
    cid: Optional[int] = None
    page: int = 1
    pages: List[Dict[str, Any]] = field(default_factory=list)
    cover_url: str = ""


@dataclass
class TextSegment:
    """A segment of extracted text with timing information.
    
    表示一段带时间戳的文本内容，可以来自字幕、ASR或OCR。
    
    Attributes:
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        text: 文本内容
        confidence: 置信度分数，范围0-1，ASR识别的置信度
        source: 文本来源，可选值：subtitle（字幕）/asr（语音识别）/ocr（光学识别）
    """

    start_time: float  # 秒
    end_time: float  # 秒
    text: str
    confidence: float = 1.0  # 0-1，ASR置信度
    source: str = "subtitle"  # subtitle/asr/ocr


@dataclass
class ExtractionResult:
    """Result of text extraction from a video.
    
    包含完整的文本提取结果，包括视频信息、文本片段和元数据。
    
    Attributes:
        video_info: 视频基本信息
        segments: 提取的文本片段列表
        method: 提取方法，可选值：subtitle（官方字幕）/asr（语音识别）/hybrid（混合方式）
        processing_time: 处理耗时（秒）
        metadata: 额外的元数据信息
    """

    video_info: VideoInfo
    segments: List[TextSegment]
    method: str  # subtitle/asr/hybrid
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptTrack:
    """A normalized transcript track available for downstream processing."""

    track_id: str
    track_type: str
    source: str
    label: str
    language: Optional[str] = None
    is_ai_generated: bool = False
    segments: List[TextSegment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptBundle:
    """Primary output contract for the acquisition and normalization stage."""

    schema_version: str
    video: Dict[str, Any]
    tracks: List[TranscriptTrack]
    selected_track: str
    quality_flags: Dict[str, Any]
    processing: Dict[str, Any]


@dataclass
class AssetRecord:
    """A single archived asset entry for replayable acquisition outputs."""

    asset_id: str
    asset_type: str
    path: str
    origin: str
    checksum: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetManifest:
    """Manifest of all archived assets generated for one video."""

    schema_version: str
    bundle_id: str
    video_id: str
    created_at: str
    status: str = "completed"
    failure_stage: Optional[str] = None
    failure_reason: str = ""
    assets: List[AssetRecord] = field(default_factory=list)
