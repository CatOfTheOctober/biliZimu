"""Logging utilities for bilibili-extractor."""

import logging
import sys
from typing import Optional
from pathlib import Path


class Logger:
    """Unified logging manager.
    
    Provides structured logging with dual output (console + file).
    Format: [时间] [级别] [模块] 消息
    
    Validates: Requirements 8.1, 8.2, 8.4, 8.5, 8.6
    """

    def __init__(self, name: str, level: str = "INFO", log_file: Optional[Path] = None):
        """Initialize logger.

        Args:
            name: Logger name (typically module name)
            level: Log level (DEBUG/INFO/WARNING/ERROR)
            log_file: Optional path to log file
        """
        self.logger = logging.getLogger(name)
        self.level = level
        self.log_file = log_file
        
        # Set log level
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create formatter: [时间] [级别] [模块] 消息
        formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler (Requirement 8.6)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (Requirement 8.6)
        if log_file:
            # Ensure parent directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Allow propagation for testing with caplog
        self.logger.propagate = True

    def info(self, message: str) -> None:
        """Log info message.

        Args:
            message: Message to log
        """
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message.

        Args:
            message: Message to log
        """
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False) -> None:
        """Log error message.

        Args:
            message: Message to log
            exc_info: Include exception info (Requirement 8.1)
        """
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message: str) -> None:
        """Log debug message.

        Args:
            message: Message to log
        """
        self.logger.debug(message)
    
    def close(self) -> None:
        """Close all handlers and release file locks.
        
        This is important on Windows to avoid file permission errors.
        """
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
