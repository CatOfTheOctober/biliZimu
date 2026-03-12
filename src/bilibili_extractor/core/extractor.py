"""Main text extractor controller."""

import time
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path

from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import ExtractionResult, VideoInfo
from bilibili_extractor.core.exceptions import SubtitleNotFoundError
from bilibili_extractor.modules.url_validator import URLValidator, URLValidationError
from bilibili_extractor.modules.video_downloader import VideoDownloader, DownloadError
from bilibili_extractor.modules.audio_extractor import AudioExtractor, AudioExtractionError
from bilibili_extractor.modules.subtitle_fetcher import SubtitleFetcher
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
        self.subtitle_fetcher = SubtitleFetcher(config)
        self._init_subtitle_fetcher()
        self.asr_engine = self._create_asr_engine()

    def _init_subtitle_fetcher(self):
        """根据配置初始化 SubtitleFetcher 的 Cookie。"""
        if self.config.cookie_file:
            cookie_path = self.config.resolve_path(self.config.cookie_file)
            if cookie_path.exists():
                try:
                    with open(cookie_path, 'r', encoding='utf-8') as f:
                        cookie_content = f.read().strip()
                        if cookie_content:
                            self.subtitle_fetcher.set_cookie(cookie_content)
                            self.logger.info(f"Loaded cookie from {self.config.cookie_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to load cookie from {self.config.cookie_file}: {e}")

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
                    model_path=self.config.funasr_model_path,
                    use_int8=self.config.use_int8 if hasattr(self.config, 'use_int8') else False,
                    use_onnx=self.config.use_onnx if hasattr(self.config, 'use_onnx') else False
                )
        except Exception as e:
            # ASR libraries not available, will be handled when needed
            self.logger.warning(f"ASR engine initialization skipped: {str(e)}")
            self.logger.warning("ASR functionality will not be available. Only videos with subtitles can be processed.")
            return None

    def _build_video_info(
        self,
        video_id: str,
        url: str,
        video_metadata: Optional[Dict[str, Any]],
        has_subtitle: bool,
    ) -> VideoInfo:
        metadata = video_metadata or {}
        published_at = metadata.get("pubdate")
        if published_at is not None:
            try:
                published_at = datetime.utcfromtimestamp(int(published_at)).isoformat() + "Z"
            except Exception:
                published_at = str(published_at)

        return VideoInfo(
            video_id=video_id,
            title=metadata.get("title", ""),
            duration=int(metadata.get("duration", 0) or 0),
            has_subtitle=has_subtitle,
            url=url,
            description=metadata.get("desc", ""),
            published_at=published_at,
            uploader=metadata.get("owner_name", ""),
            cid=metadata.get("cid"),
            page=int(metadata.get("page", 1) or 1),
            pages=list(metadata.get("pages", [])),
            cover_url=metadata.get("pic", ""),
        )

    def _archive_extraction(
        self,
        result: ExtractionResult,
        artifact_dir: Path,
        video_path: Optional[Path],
        audio_path: Optional[Path],
        subtitle_details: Optional[Dict[str, Any]],
        video_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from bilibili_extractor.modules.acquisition_bundle import AcquisitionBundleBuilder

        builder = AcquisitionBundleBuilder(self.config)
        subtitle_result = (subtitle_details or {}).get("subtitle_result", {})
        return builder.export(
            result=result,
            output_root=artifact_dir,
            raw_video_path=video_path,
            raw_audio_path=audio_path,
            raw_subtitle_payload=subtitle_result.get("raw_subtitle_data") or subtitle_result or None,
            raw_video_metadata=video_metadata,
            selected_track_metadata=(subtitle_details or {}).get("selected_track"),
        )

    def _archive_failure(
        self,
        artifact_dir: Path,
        video_id: str,
        title: str,
        failure_stage: str,
        failure_reason: str,
        video_path: Optional[Path],
        subtitle_details: Optional[Dict[str, Any]],
        video_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from bilibili_extractor.modules.acquisition_bundle import AcquisitionBundleBuilder

        builder = AcquisitionBundleBuilder(self.config)
        subtitle_result = (subtitle_details or {}).get("subtitle_result", {})
        return builder.export_failure(
            output_root=artifact_dir,
            video_id=video_id,
            title=title,
            raw_video_path=video_path,
            raw_subtitle_payload=subtitle_result.get("raw_subtitle_data") or subtitle_result or None,
            raw_video_metadata=video_metadata,
            failure_stage=failure_stage,
            failure_reason=failure_reason,
        )

    def _fetch_video_metadata(self, video_id: str, url: str) -> Optional[Dict[str, Any]]:
        if not hasattr(self.subtitle_fetcher, "get_video_metadata"):
            return None
        try:
            return self.subtitle_fetcher.get_video_metadata(video_id, url)
        except Exception as e:
            self.logger.warning(f"Failed to fetch video metadata: {e}")
            return None

    def _fetch_subtitle_details(self, video_id: str, url: str) -> Dict[str, Any]:
        fetch_method = getattr(self.subtitle_fetcher, "fetch_subtitle_details", None)
        if not callable(fetch_method):
            raise SubtitleNotFoundError("SubtitleFetcher does not provide fetch_subtitle_details")

        details = fetch_method(video_id, url)
        if not isinstance(details, dict):
            raise SubtitleNotFoundError("API subtitle details are unavailable")

        segments = details.get("segments")
        if not isinstance(segments, list) or not segments:
            raise SubtitleNotFoundError("API获取字幕失败。")
        return details

    def _build_subtitle_result(
        self,
        video_id: str,
        url: str,
        segments: List[Any],
        video_metadata: Optional[Dict[str, Any]],
        subtitle_details: Optional[Dict[str, Any]],
        processing_time: float,
    ) -> ExtractionResult:
        video_info = self._build_video_info(
            video_id=video_id,
            url=url,
            video_metadata=video_metadata,
            has_subtitle=True,
        )
        return ExtractionResult(
            video_info=video_info,
            segments=segments,
            method="subtitle",
            processing_time=processing_time,
            metadata={
                "segment_count": len(segments),
                "extraction_method": "subtitle",
                "source": "api",
                "subtitle_kind": "ai" if (subtitle_details or {}).get("selected_track", {}).get("is_ai_generated") else "official",
                "video_metadata": video_metadata or {},
            },
        )

    def extract(
        self,
        url: str,
        progress_callback: Optional[Callable] = None,
        force_asr: bool = False,
        artifact_dir: Optional[Path] = None,
    ) -> ExtractionResult:
        """从URL中提取文本内容。
        
        Args:
            url: 视频URL
            progress_callback: 进度回调函数
            force_asr: 是否强制开启 ASR 流程 (如果为 False 且 API 无字幕，将停止并抛出异常)
            
        Returns:
            ExtractionResult 对象
            
        Raises:
            SubtitleNotFoundError: 如果未找到 API 字幕且 force_asr 为 False
        """
        start_time = time.time()
        video_path = None
        audio_path = None
        subtitle_details = None
        video_metadata = None
        
        try:
            # 1. 验证URL (Requirement 1.1)
            self.logger.info("Step 1: 验证URL")
            if not URLValidator.validate(url):
                error_msg = f"Invalid URL: {url}"
                self.logger.error(error_msg)
                raise URLValidationError(error_msg)
            
            video_id = URLValidator.extract_video_id(url)
            self.logger.info(f"目标视频: {video_id}")
            video_metadata = self._fetch_video_metadata(video_id, url)

            # 2. 下载视频 (硬前置原始资产)
            self.logger.info("Step 2: 下载视频")
            video_path = self.video_downloader.download(video_id, progress_callback)
            self.logger.info(f"视频已下载: {video_path}")
            self.resource_manager.register_file(video_path)
            
            if not force_asr:
                self.logger.info("Step 3: 尝试通过 API 获取字幕 (AI 字幕优先)")
                try:
                    subtitle_details = self._fetch_subtitle_details(video_id, url)
                    if subtitle_details.get("video_info"):
                        video_metadata = subtitle_details.get("video_info")
                    segments = subtitle_details["segments"]
                    self.logger.info(f"成功获取 API 字幕! 共 {len(segments)} 条片段")

                    processing_time = time.time() - start_time
                    result = self._build_subtitle_result(
                        video_id=video_id,
                        url=url,
                        segments=segments,
                        video_metadata=video_metadata,
                        subtitle_details=subtitle_details,
                        processing_time=processing_time,
                    )
                    if artifact_dir is not None:
                        archive_info = self._archive_extraction(
                            result=result,
                            artifact_dir=artifact_dir,
                            video_path=video_path,
                            audio_path=None,
                            subtitle_details=subtitle_details,
                            video_metadata=video_metadata,
                        )
                        result.metadata["artifact_bundle_dir"] = str(archive_info["bundle_dir"])
                        result.metadata["artifact_manifest_path"] = str(archive_info["manifest_path"])
                    return result
                except SubtitleNotFoundError as e:
                    if artifact_dir is not None:
                        failed_info = self._archive_failure(
                            artifact_dir=artifact_dir,
                            video_id=video_id,
                            title=(video_metadata or {}).get("title", video_id),
                            failure_stage="subtitle_fetch",
                            failure_reason=str(e),
                            video_path=video_path,
                            subtitle_details=subtitle_details,
                            video_metadata=video_metadata,
                        )
                        self.logger.warning(f"字幕获取失败，失败包已写入: {failed_info['bundle_dir']}")
                    raise

            self.logger.info("Step 3: 提取音频")
            audio_path = self.audio_extractor.extract(video_path)
            self.logger.info(f"音频已提取: {audio_path}")
            self.resource_manager.register_file(audio_path)
            
            self.logger.info(f"Step 4: 运行 ASR识别 ({self.config.asr_engine})")
            if self.asr_engine is None:
                error_msg = (
                    f"No ASR engine available for video {video_id}.\n"
                    f"To use ASR functionality, please install one of the following:\n"
                    f"  - FunASR (recommended for Chinese): pip install funasr\n"
                    f"  - Whisper (multilingual): pip install openai-whisper"
                )
                self.logger.error(error_msg)
                raise ASRError(error_msg)

            try:
                segments = self.asr_engine.transcribe(audio_path, progress_callback)
                self.logger.info(f"ASR 识别完成: {len(segments)} segments")
                for segment in segments:
                    segment.source = 'asr'
            except FileNotFoundError as e:
                error_msg = (
                    f"💔 ASR 本地模型库未安装呐: {str(e)}\n"
                    f"👉 请手动配置好网络环境后执行安装指令:\n"
                    f"  - 对于 FunASR 识别引擎 (推荐中文环境): pip install funasr\n"
                    f"  - 对于 Whisper 引擎 (多语言环境): pip install openai-whisper\n"
                    f"✨ (温馨提示: 如果遇到网络问题，可以尝试加参数 -i https://pypi.tuna.tsinghua.edu.cn/simple 哟~)"
                )
                self.logger.error(error_msg)
                raise ASRError(error_msg)
            
            processing_time = time.time() - start_time
            self.logger.info("Step 5: Generating extraction result")
            video_info = self._build_video_info(
                video_id=video_id,
                url=url,
                video_metadata=video_metadata,
                has_subtitle=False,
            )
            result = ExtractionResult(
                video_info=video_info,
                segments=segments,
                method="asr",
                processing_time=processing_time,
                metadata={
                    "segment_count": len(segments),
                    "extraction_method": "asr",
                    "asr_engine": self.config.asr_engine,
                    "video_metadata": video_metadata or {},
                }
            )

            if artifact_dir is not None:
                archive_info = self._archive_extraction(
                    result=result,
                    artifact_dir=artifact_dir,
                    video_path=video_path,
                    audio_path=audio_path,
                    subtitle_details={
                        "selected_track": {
                            "track_id": "selected_asr",
                            "track_type": "asr",
                            "source": "asr",
                            "label": "ASR",
                            "language": self.config.language,
                            "is_ai_generated": False,
                            "asr_engine": self.config.asr_engine,
                        }
                    },
                    video_metadata=video_metadata,
                )
                result.metadata["artifact_bundle_dir"] = str(archive_info["bundle_dir"])
                result.metadata["artifact_manifest_path"] = str(archive_info["manifest_path"])

            self.logger.info(
                f"Extraction complete: {len(segments)} segments, "
                f"method: asr, "
                f"processing time: {processing_time:.2f}s"
            )
            return result
             
        except DownloadError as e:
            if artifact_dir is not None:
                failed_info = self._archive_failure(
                    artifact_dir=artifact_dir,
                    video_id=video_id if 'video_id' in locals() else "unknown",
                    title=(video_metadata or {}).get("title", video_id if 'video_id' in locals() else "unknown"),
                    failure_stage="video_download",
                    failure_reason=str(e),
                    video_path=video_path,
                    subtitle_details=subtitle_details,
                    video_metadata=video_metadata,
                )
                self.logger.warning(f"视频下载失败，失败包已写入: {failed_info['bundle_dir']}")
            raise
        except SubtitleNotFoundError:
            raise
        except (URLValidationError, AudioExtractionError, ASRError) as e:
            if artifact_dir is not None and 'video_id' in locals():
                failed_info = self._archive_failure(
                    artifact_dir=artifact_dir,
                    video_id=video_id,
                    title=(video_metadata or {}).get("title", video_id),
                    failure_stage="asr" if force_asr else "processing",
                    failure_reason=str(e),
                    video_path=video_path,
                    subtitle_details=subtitle_details,
                    video_metadata=video_metadata,
                )
                self.logger.warning(f"流程失败，失败包已写入: {failed_info['bundle_dir']}")
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
