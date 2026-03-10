"""Main text extractor controller."""

import time
from typing import Optional, Callable, List
from pathlib import Path

from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import ExtractionResult, VideoInfo
from bilibili_extractor.core.exceptions import SubtitleNotFoundError
from bilibili_extractor.modules.url_validator import URLValidator, URLValidationError
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
        self.resource_manager = ResourceManager(str(config.resolved_temp_dir), config.keep_temp_files)
        self.auth_manager = AuthManager(config)
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
        """Extract text from a Bilibili video using ASR.
        
        Implements video processing flow:
        1. Validate URL
        2. Download full video → extract audio → ASR
        
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
            self.logger.info("Step 1: 验证URL")
            if not URLValidator.validate(url):
                error_msg = f"Invalid URL: {url}"
                self.logger.error(error_msg)
                raise URLValidationError(error_msg)
            
            video_id = URLValidator.extract_video_id(url)
            self.logger.info(f"目标视频: {video_id}")
            
            # Check if ASR engine is available
            if self.asr_engine is None:
                error_msg = (
                    f"No ASR engine available for video {video_id}.\n"
                    f"To use ASR functionality, please install one of the following:\n"
                    f"  - FunASR (recommended for Chinese): pip install funasr\n"
                    f"  - Whisper (multilingual): pip install openai-whisper"
                )
                self.logger.error(error_msg)
                raise ASRError(error_msg)
            
            # 2. 下载视频 (Requirement 3.1)
            self.logger.info("Step 2: 下载视频")
            video_path = self.video_downloader.download(video_id, progress_callback)
            self.logger.info(f"视频已下载: {video_path}")
            self.resource_manager.register_file(video_path)
            # 3. 提取音频 (Requirement 4.1)
            self.logger.info("Step 3: 提取音频")
            audio_path = self.audio_extractor.extract(video_path)
            self.logger.info(f"音频已提取: {audio_path}")
            self.resource_manager.register_file(audio_path)
            
            # 4. ASR识别 (Requirement 5.1)
            self.logger.info(f"Step 4: 运行 ASR识别 ({self.config.asr_engine})")
            try:
                segments = self.asr_engine.transcribe(audio_path, progress_callback)
                self.logger.info(f"ASR 识别完成: {len(segments)} segments")
                
                # 确保ASR生成的segments的source为'asr'
                for segment in segments:
                    segment.source = 'asr'
                    
            except FileNotFoundError as e:
                # ASR library not installed
                error_msg = (
                    f"💔 ASR 本地模型库未安装呐: {str(e)}\n"
                    f"👉 请手动配置好网络环境后执行安装指令:\n"
                    f"  - 对于 FunASR 识别引擎 (推荐中文环境): pip install funasr\n"
                    f"  - 对于 Whisper 引擎 (多语言环境): pip install openai-whisper\n"
                    f"✨ (温馨提示: 如果遇到网络问题，可以尝试加参数 -i https://pypi.tuna.tsinghua.edu.cn/simple 哟~)"
                )
                self.logger.error(error_msg)
                raise ASRError(error_msg)
            
            method = "asr"
            
            # 5. 计算处理时间 (Requirement 8.2)
            processing_time = time.time() - start_time
            
            # 6. 生成结果 (Requirement 7.1)
            self.logger.info("Step 5: Generating extraction result")
            result = ExtractionResult(
                video_info=VideoInfo(
                    video_id=video_id,
                    title="",  # Will be populated in future tasks
                    duration=0,  # Will be populated in future tasks
                    has_subtitle=False,
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
        
        except (URLValidationError, DownloadError, AudioExtractionError, ASRError):
            # Re-raise these exceptions as-is
            raise
        except Exception as e:
            # Log unexpected errors (Requirement 8.1)
            self.logger.error(f"Unexpected error during extraction: {str(e)}", exc_info=True)
            raise
        finally:
            # 7. 清理资源 (Requirement 9.1)
            self.logger.info("Step 6: Cleaning up resources")
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
