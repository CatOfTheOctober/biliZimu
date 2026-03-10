"""OCR (Optical Character Recognition) engine for hard subtitles."""

from typing import List, Optional, Tuple
from pathlib import Path
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import TextSegment


class OCREngine:
    """Extract text from video frames using OCR."""

    def __init__(self, config: Config):
        """Initialize OCR engine.

        Args:
            config: Configuration object
        """
        self.config = config

    def detect_subtitle_region(self, video_path: Path) -> Optional[Tuple[int, int, int, int]]:
        """Detect subtitle region in video frames.

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (x, y, width, height) or None if no subtitles detected
        """
        raise NotImplementedError("Will be implemented in task 18")

    def extract_text_from_frames(
        self, video_path: Path, region: Optional[Tuple[int, int, int, int]]
    ) -> List[TextSegment]:
        """Extract text from video frames.

        Args:
            video_path: Path to video file
            region: Optional region to focus on (x, y, width, height)

        Returns:
            List of TextSegment objects
        """
        raise NotImplementedError("Will be implemented in task 18")

    def merge_with_asr(
        self, ocr_segments: List[TextSegment], asr_segments: List[TextSegment]
    ) -> List[TextSegment]:
        """Merge OCR and ASR results.

        Args:
            ocr_segments: Segments from OCR
            asr_segments: Segments from ASR

        Returns:
            Merged list of TextSegment objects
        """
        raise NotImplementedError("Will be implemented in task 18")
