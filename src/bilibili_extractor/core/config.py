"""Configuration management for bilibili-extractor."""

from dataclasses import dataclass, field, fields
from typing import Optional, Dict, Any
from pathlib import Path
import yaml
import argparse
import logging


@dataclass
class Config:
    """Configuration for bilibili-extractor."""

    # General settings
    temp_dir: str = "./temp"
    output_dir: str = "./output"
    log_level: str = "INFO"
    keep_temp_files: bool = False

    # Tool paths (relative to project root)
    bbdown_path: Optional[str] = None  # Auto-detect if None
    ffmpeg_path: Optional[str] = None  # Auto-detect if None
    ffprobe_path: Optional[str] = None  # Auto-detect if None

    # Download settings
    cookie_file: Optional[str] = None
    auto_login: bool = True
    login_type: str = 'web'  # 'web' or 'tv'
    video_quality: str = "720P"  # 480P/720P/1080P
    download_threads: int = 4

    # ASR settings
    asr_engine: str = "funasr"  # funasr/whisper
    funasr_model: str = "paraformer-zh"
    whisper_model: str = "base"
    language: Optional[str] = None
    use_int8: bool = False  # INT8 quantization for FunASR
    use_onnx: bool = False  # ONNX Runtime for FunASR

    # OCR settings
    enable_ocr: bool = False
    ocr_engine: str = "paddleocr"

    # Output settings
    output_format: str = "txt"  # srt/json/txt/markdown
    
    # API 请求配置
    api_request_interval: int = 20  # API 请求间隔（秒）
    api_retry_max_attempts: int = 3  # API 重试最大次数
    api_retry_wait_time: int = 20  # API 重试等待时间（秒）
    
    def resolve_path(self, path: str) -> Path:
        """解析路径，相对路径相对于项目根目录。
        
        Args:
            path: 路径字符串
            
        Returns:
            解析后的绝对路径
        """
        from ..utils.tool_finder import ToolFinder
        
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        
        # 相对路径，相对于项目根目录
        tool_finder = ToolFinder()
        project_root = tool_finder.get_project_root()
        return project_root / path


class ConfigLoader:
    """Load and validate configuration."""

    @staticmethod
    def load_from_file(config_path: Path) -> Config:
        """Load configuration from YAML file."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Flatten nested structure if needed
        config_dict: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                config_dict.update(value)
            else:
                config_dict[key] = value

        return Config(**config_dict)

    @staticmethod
    def load_from_args(args: argparse.Namespace) -> Config:
        """Load configuration from command line arguments.
        
        Only includes arguments that are explicitly set (not None).
        """
        config_dict: Dict[str, Any] = {}
        
        # Map CLI argument names to Config field names
        arg_mapping = {
            'temp_dir': 'temp_dir',
            'output_dir': 'output_dir',
            'log_level': 'log_level',
            'keep_temp': 'keep_temp_files',
            'cookie': 'cookie_file',
            'auto_login': 'auto_login',
            'login_type': 'login_type',
            'video_quality': 'video_quality',
            'download_threads': 'download_threads',
            'asr_engine': 'asr_engine',
            'funasr_model': 'funasr_model',
            'whisper_model': 'whisper_model',
            'language': 'language',
            'use_int8': 'use_int8',
            'use_onnx': 'use_onnx',
            'enable_ocr': 'enable_ocr',
            'ocr_engine': 'ocr_engine',
            'format': 'output_format',
        }
        
        # Extract non-None arguments
        for arg_name, config_name in arg_mapping.items():
            if hasattr(args, arg_name):
                value = getattr(args, arg_name)
                if value is not None:
                    config_dict[config_name] = value
        
        return Config(**config_dict)

    @staticmethod
    def merge_configs(file_config: Config, args_config: Config) -> Config:
        """Merge configurations, with command line arguments taking priority.
        
        Args:
            file_config: Configuration loaded from file
            args_config: Configuration loaded from command line arguments
            
        Returns:
            Merged configuration with CLI args overriding file config
        """
        # Start with file config as base
        merged_dict = {
            field.name: getattr(file_config, field.name)
            for field in fields(Config)
        }
        
        # Override with args config (only non-default values)
        default_config = Config()
        for field in fields(Config):
            args_value = getattr(args_config, field.name)
            default_value = getattr(default_config, field.name)
            
            # If args value differs from default, it was explicitly set
            if args_value != default_value:
                merged_dict[field.name] = args_value
        
        return Config(**merged_dict)

    @staticmethod
    def validate_config(config: Config) -> bool:
        """Validate configuration parameters.
        
        Per Requirement 11.10: If configuration parameters are invalid,
        the system should use default values and issue warnings.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if validation succeeds (with or without warnings)
        """
        logger = logging.getLogger(__name__)
        default_config = Config()
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if config.log_level not in valid_log_levels:
            logger.warning(
                f"Invalid log_level '{config.log_level}'. "
                f"Using default: {default_config.log_level}"
            )
            config.log_level = default_config.log_level

        # Validate video quality
        valid_qualities = ["480P", "720P", "1080P"]
        if config.video_quality not in valid_qualities:
            logger.warning(
                f"Invalid video_quality '{config.video_quality}'. "
                f"Using default: {default_config.video_quality}"
            )
            config.video_quality = default_config.video_quality

        # Validate ASR engine
        valid_asr_engines = ["funasr", "whisper"]
        if config.asr_engine not in valid_asr_engines:
            logger.warning(
                f"Invalid asr_engine '{config.asr_engine}'. "
                f"Using default: {default_config.asr_engine}"
            )
            config.asr_engine = default_config.asr_engine

        # Validate whisper model
        valid_whisper_models = ["tiny", "base", "small", "medium", "large"]
        if config.whisper_model not in valid_whisper_models:
            logger.warning(
                f"Invalid whisper_model '{config.whisper_model}'. "
                f"Using default: {default_config.whisper_model}"
            )
            config.whisper_model = default_config.whisper_model

        # Validate OCR engine
        valid_ocr_engines = ["paddleocr", "tesseract"]
        if config.ocr_engine not in valid_ocr_engines:
            logger.warning(
                f"Invalid ocr_engine '{config.ocr_engine}'. "
                f"Using default: {default_config.ocr_engine}"
            )
            config.ocr_engine = default_config.ocr_engine

        # Validate output format
        valid_formats = ["srt", "json", "txt", "markdown"]
        if config.output_format not in valid_formats:
            logger.warning(
                f"Invalid output_format '{config.output_format}'. "
                f"Using default: {default_config.output_format}"
            )
            config.output_format = default_config.output_format

        # Validate download threads (must be > 0)
        if config.download_threads <= 0:
            logger.warning(
                f"Invalid download_threads '{config.download_threads}' (must be > 0). "
                f"Using default: {default_config.download_threads}"
            )
            config.download_threads = default_config.download_threads

        # Validate API request interval (must be > 0)
        if config.api_request_interval <= 0:
            logger.warning(
                f"Invalid api_request_interval '{config.api_request_interval}' (must be > 0). "
                f"Using default: {default_config.api_request_interval}"
            )
            config.api_request_interval = default_config.api_request_interval

        # Validate API retry max attempts (must be > 0)
        if config.api_retry_max_attempts <= 0:
            logger.warning(
                f"Invalid api_retry_max_attempts '{config.api_retry_max_attempts}' (must be > 0). "
                f"Using default: {default_config.api_retry_max_attempts}"
            )
            config.api_retry_max_attempts = default_config.api_retry_max_attempts

        # Validate API retry wait time (must be > 0)
        if config.api_retry_wait_time <= 0:
            logger.warning(
                f"Invalid api_retry_wait_time '{config.api_retry_wait_time}' (must be > 0). "
                f"Using default: {default_config.api_retry_wait_time}"
            )
            config.api_retry_wait_time = default_config.api_retry_wait_time

        return True
