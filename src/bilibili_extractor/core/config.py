"""Configuration management for bilibili-extractor."""

from dataclasses import dataclass, field, fields
from typing import Optional, Dict, Any
from pathlib import Path
import yaml
import argparse
import logging


@dataclass
class Config:
    """Configuration for bilibili-extractor.
    
    All default values should ideally be managed via config/default_config.yaml.
    The values here serve as a final fallback or represent the structure.
    """

    # General settings
    temp_dir: str = field(default="./temp")
    output_dir: str = field(default="./output")
    log_level: str = field(default="INFO")
    keep_temp_files: bool = field(default=False)

    # Tool paths (relative to project root)
    bbdown_path: Optional[str] = field(default=None)
    ffmpeg_path: Optional[str] = field(default=None)
    ffprobe_path: Optional[str] = field(default=None)

    # Download settings
    cookie_file: Optional[str] = field(default="tools/BBDown/BBDown.data")
    auto_login: bool = field(default=True)
    login_type: str = field(default='web')  # 'web' or 'tv'
    video_quality: str = field(default="720P")
    download_threads: int = field(default=4)

    # ASR settings
    asr_engine: str = field(default="funasr")
    funasr_model: str = field(default="paraformer-zh")
    funasr_model_path: Optional[str] = field(default="D:/Model/Funasr_model")
    whisper_model: str = field(default="base")
    language: Optional[str] = field(default=None)
    use_int8: bool = field(default=False)
    use_onnx: bool = field(default=False)

    # OCR settings (Legacy/Future)
    enable_ocr: bool = field(default=False)
    ocr_engine: str = field(default="paddleocr")

    # Output settings
    output_format: str = field(default="txt")
    
    # API 请求配置
    api_request_interval: int = field(default=20)
    api_retry_max_attempts: int = field(default=3)
    api_retry_wait_time: int = field(default=20)
    
    # 内部存储解析后的路径
    _resolved_temp_dir: Optional[Path] = None
    _resolved_output_dir: Optional[Path] = None
    
    def __post_init__(self):
        """初始化后处理，解析路径。"""
        # 延迟导入以避免循环导入
        from ..utils.tool_finder import ToolFinder
        
        # 尝试从默认位置加载 Cookie 内容（如果存在）
        if self.cookie_file:
            cookie_path = self.resolve_path(self.cookie_file)
            if cookie_path.exists() and cookie_path.is_file():
                try:
                    with open(cookie_path, 'r', encoding='utf-8') as f:
                        # 如果没有显式设置 cookie 字符串，这里不直接修改类属性，
                        # 但我们可以在需要的地方使用这个 resolve_path(self.cookie_file)
                        pass
                except Exception:
                    pass
        
        # 解析临时目录路径
        temp_path = Path(self.temp_dir)
        if not temp_path.is_absolute():
            tool_finder = ToolFinder()
            project_root = tool_finder.get_project_root()
            self._resolved_temp_dir = project_root / self.temp_dir
        else:
            self._resolved_temp_dir = temp_path
        
        # 解析输出目录路径
        output_path = Path(self.output_dir)
        if not output_path.is_absolute():
            tool_finder = ToolFinder()
            project_root = tool_finder.get_project_root()
            self._resolved_output_dir = project_root / self.output_dir
        else:
            self._resolved_output_dir = output_path
    
    @property
    def resolved_temp_dir(self) -> Path:
        """获取解析后的临时目录路径。
        
        Returns:
            解析后的临时目录路径
        """
        if self._resolved_temp_dir is None:
            self.__post_init__()
        return self._resolved_temp_dir
    
    @property
    def resolved_output_dir(self) -> Path:
        """获取解析后的输出目录路径。
        
        Returns:
            解析后的输出目录路径
        """
        if self._resolved_output_dir is None:
            self.__post_init__()
        return self._resolved_output_dir
    
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
