"""Bilibili Video Text Extractor

Extract text from Bilibili videos using subtitles, ASR, and OCR.
"""

__version__ = "1.0.0"

from bilibili_extractor.core.models import VideoInfo, TextSegment, ExtractionResult
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.extractor import TextExtractor

__all__ = [
    "VideoInfo",
    "TextSegment",
    "ExtractionResult",
    "Config",
    "TextExtractor",
]
