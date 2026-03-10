"""Main text extractor controller."""

import time
from typing import Optional, Callable, List
from pathlib import Path

from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import ExtractionResult, VideoInfo
from bilibili_extractor.core.exceptions import SubtitleNotFoundError
from bilibili_extractor.modules.url_validator import URLValidator, URLValidationError
from bilibili_extractor.modules.subtitle_fetcher import SubtitleFetcher
from bilibili_extractor.modules.video_downloader import VideoDownloader, DownloadError
from bilibili_extractor.modules.audio_extractor import AudioExtractor, AudioExtractionError
from bilibili_extractor.modules.asr_engine import ASREngine, FunASREngine, WhisperEngine, ASRError
from bilibili_extractor.modules.auth_manager import AuthManager
from bilibili_extractor.utils.logger import Logger
from bilibili_extractor.utils.resource_manager import ResourceManager


class TextExtractor:
    """Main controller for text extraction from Bilibili videos.
    
    Validates: Requirements 1.1, 2.1, 2.2, 2.7, 3.1, 4.1, 5.1, 7.1, 8.1, 8.2, 9.1
    """

    def __init__(self, config: Config):
        """Initialize the text extractor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger("TextExtractor", config.log_level)
        self.resource_manager = ResourceManager(config.temp_dir, config.keep_temp_files)
        self.auth_manager = AuthManager(config)
        self.subtitle_fetcher = SubtitleFetcher(config)
        self.video_downloader = VideoDownloader(config)
        self.audio_extractor = AudioExtractor()
        self.asr_engine = self._create_asr_engine()

    def _create_asr_engine(self) -> Optional[ASREngine]:
        """Create ASR engine based on configuration.
        
        Returns:
            ASREngine instance (FunASR or Whisper), or None if libraries not available
        """
        try:
            if self.config.asr_engine == "whisper":
                return WhisperEngine(
                    model=self.config.whisper_model,
                    language=self.config.language
                )
            else:  # Default to FunASR
                return FunASREngine(
                    model=self.config.funasr_model,
                    use_int8=self.config.use_int8 if hasattr(self.config, 'use_int8') else False,
                    use_onnx=self.config.use_onnx if hasattr(self.config, 'use_onnx') else False
                )
        except Exception as e:
            # ASR libraries not available, will be handled when needed
            self.logger.warning(f"ASR engine initialization skipped: {str(e)}")
            self.logger.warning("ASR functionality will not be available. Only videos with subtitles can be processed.")
            return None

    def extract(self, url: str, progress_callback: Optional[Callable] = None) -> ExtractionResult:
        """Extract text from a Bilibili video.
        
        Implements two-stage processing flow:
        1. Try BBDown --sub-only to download subtitles
        2. If no subtitles exist, use BBDown to download full video → extract audio → ASR

        Args:
            url: Bilibili video URL
            progress_callback: Optional callback for progress updates

        Returns:
            ExtractionResult containing extracted text segments
            
        Raises:
            URLValidationError: If URL is invalid
            DownloadError: If video download fails
            AudioExtractionError: If audio extraction fails
            ASRError: If ASR processing fails
        """
        start_time = time.time()
        
        try:
            # 1. 验证URL (Requirement 1.1)
            self.logger.info("Step 1: Validating URL")
            if not URLValidator.validate(url):
                error_msg = f"Invalid URL: {url}"
                self.logger.error(error_msg)
                raise URLValidationError(error_msg)
            
            video_id = URLValidator.extract_video_id(url)
            self.logger.info(f"Processing video: {video_id}")
            
            # 1.5. Cookie管理和初始化BilibiliAPI
            self.logger.info("Step 1.5: Checking Cookie")
            if self.auth_manager.check_cookie():
                cookie_path = self.auth_manager.get_cookie_path()
                self.logger.info(f"Cookie found: {cookie_path}")
                
                # 读取Cookie内容
                cookie_content = self.auth_manager.read_cookie_content(cookie_path)
                
                # 设置Cookie到SubtitleFetcher
                self.subtitle_fetcher.set_cookie(cookie_content)
                self.logger.info("BilibiliAPI initialized with cookie")
            else:
                self.logger.info("No cookie found, Bilibili API will not be available")
            
            # 2. 尝试获取字幕（优先Bilibili API）
            self.logger.info("Step 2: Checking for subtitles")
            segments = self.subtitle_fetcher.fetch_subtitle(video_id, url)
            
            if segments:
                self.logger.info(f"Subtitle fetched: {len(segments)} segments")
                method = "subtitle"
            else:
                # 字幕不存在，降级到ASR流程
                self.logger.info("No subtitles found, proceeding with ASR workflow")
                
                # Check if ASR engine is available
                if self.asr_engine is None:
                    error_msg = (
                        f"No subtitles found for video {video_id} and ASR is not available.\n"
                        f"To use ASR functionality, please install one of the following:\n"
                        f"  - FunASR (recommended for Chinese): pip install funasr\n"
                        f"  - Whisper (multilingual): pip install openai-whisper\n"
                        f"Alternatively, try a video with official subtitles."
                    )
                    self.logger.error(error_msg)
                    raise SubtitleNotFoundError(error_msg)
                
                # 3a. 下载视频 (Requirement 3.1)
                self.logger.info("Step 3: Downloading video")
                video_path = self.video_downloader.download(video_id, progress_callback)
                self.logger.info(f"Video downloaded: {video_path}")
                self.resource_manager.register_file(video_path)
                
                # 3b. 提取音频 (Requirement 4.1)
                self.logger.info("Step 4: Extracting audio")
                audio_path = self.audio_extractor.extract(video_path)
                self.logger.info(f"Audio extracted: {audio_path}")
                self.resource_manager.register_file(audio_path)
                
                # 3c. ASR识别 (Requirement 5.1)
                self.logger.info(f"Step 5: Running ASR ({self.config.asr_engine})")
                try:
                    segments = self.asr_engine.transcribe(audio_path, progress_callback)
                    self.logger.info(f"ASR completed: {len(segments)} segments")
                    
                    # 确保ASR生成的segments的source为'asr'
                    for segment in segments:
                        segment.source = 'asr'
                        
                except FileNotFoundError as e:
                    # ASR library not installed
                    error_msg = (
                        f"ASR library not installed: {str(e)}\n"
                        f"Please install the required library:\n"
                        f"  - For FunASR: pip install funasr\n"
                        f"  - For Whisper: pip install openai-whisper"
                    )
                    self.logger.error(error_msg)
                    raise ASRError(error_msg)
                
                method = "asr"
            
            # 4. 计算处理时间 (Requirement 8.2)
            processing_time = time.time() - start_time
            
            # 5. 生成结果 (Requirement 7.1)
            self.logger.info("Step 6: Generating extraction result")
            result = ExtractionResult(
                video_info=VideoInfo(
                    video_id=video_id,
                    title="",  # Will be populated in future tasks
                    duration=0,  # Will be populated in future tasks
                    has_subtitle=method == "subtitle",
                    url=url
                ),
                segments=segments,
                method=method,
                processing_time=processing_time,
                metadata={
                    "segment_count": len(segments),
                    "extraction_method": method,
                    "asr_engine": self.config.asr_engine if method == "asr" else None
                }
            )
            
            self.logger.info(
                f"Extraction complete: {len(segments)} segments, "
                f"method: {method}, "
                f"processing time: {processing_time:.2f}s"
            )
            
            return result
        
        except (URLValidationError, SubtitleNotFoundError, DownloadError, AudioExtractionError, ASRError):
            # Re-raise these exceptions as-is
            raise
        except Exception as e:
            # Log unexpected errors (Requirement 8.1)
            self.logger.error(f"Unexpected error during extraction: {str(e)}", exc_info=True)
            raise
        finally:
            # 6. 清理资源 (Requirement 9.1)
            self.logger.info("Step 7: Cleaning up resources")
            self.resource_manager.cleanup()
            self.logger.close()

    def extract_batch(self, urls: List[str]) -> List[ExtractionResult]:
        """Extract text from multiple videos.
        
        Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
        
        Implements batch processing with error isolation:
        - Process videos sequentially
        - Single failure doesn't affect other videos
        - Generate summary report at the end

        Args:
            urls: List of Bilibili video URLs

        Returns:
            List of ExtractionResult objects (successful extractions only)
        """
        self.logger.info(f"Starting batch processing: {len(urls)} videos")
        
        results = []
        failed_urls = []
        
        # Process each URL sequentially (Requirement 12.2)
        for i, url in enumerate(urls, 1):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing video {i}/{len(urls)}: {url}")
            self.logger.info(f"{'='*60}")
            
            try:
                # Extract text from video
                result = self.extract(url)
                results.append(result)
                self.logger.info(f"✓ Video {i}/{len(urls)} completed successfully")
                
            except Exception as e:
                # Single failure doesn't affect other videos (Requirement 12.4)
                self.logger.error(f"✗ Video {i}/{len(urls)} failed: {str(e)}")
                failed_urls.append((url, str(e)))
                # Continue processing other videos
                continue
        
        # Generate summary report (Requirements 12.5, 12.6)
        self.logger.info(f"\n{'='*60}")
        self.logger.info("Batch Processing Summary")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total videos: {len(urls)}")
        self.logger.info(f"Successful: {len(results)}")
        self.logger.info(f"Failed: {len(failed_urls)}")
        
        if failed_urls:
            self.logger.info("\nFailed videos:")
            for url, error in failed_urls:
                self.logger.info(f"  - {url}")
                self.logger.info(f"    Error: {error}")
        
        self.logger.info(f"{'='*60}\n")
        
        return results
