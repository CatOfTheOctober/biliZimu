"""Unit tests for Logger class."""

import logging
import tempfile
from pathlib import Path

import pytest

from bilibili_extractor.utils.logger import Logger


def test_logger_initialization():
    """Test logger can be initialized with default parameters."""
    logger = Logger("test_module")
    assert logger.logger.name == "test_module"
    assert logger.level == "INFO"
    assert logger.log_file is None


def test_logger_with_custom_level():
    """Test logger respects custom log level."""
    logger = Logger("test_module", level="DEBUG")
    assert logger.level == "DEBUG"
    assert logger.logger.level == logging.DEBUG


def test_logger_info_message(caplog):
    """Test info logging."""
    logger = Logger("test_module", level="INFO")
    
    with caplog.at_level(logging.INFO):
        logger.info("Test info message")
    
    assert "Test info message" in caplog.text
    assert "INFO" in caplog.text


def test_logger_warning_message(caplog):
    """Test warning logging."""
    logger = Logger("test_module", level="WARNING")
    
    with caplog.at_level(logging.WARNING):
        logger.warning("Test warning message")
    
    assert "Test warning message" in caplog.text
    assert "WARNING" in caplog.text


def test_logger_error_message(caplog):
    """Test error logging."""
    logger = Logger("test_module", level="ERROR")
    
    with caplog.at_level(logging.ERROR):
        logger.error("Test error message")
    
    assert "Test error message" in caplog.text
    assert "ERROR" in caplog.text


def test_logger_error_with_exc_info(caplog):
    """Test error logging with exception info."""
    logger = Logger("test_module", level="ERROR")
    
    try:
        raise ValueError("Test exception")
    except ValueError:
        with caplog.at_level(logging.ERROR):
            logger.error("Error occurred", exc_info=True)
    
    assert "Error occurred" in caplog.text
    assert "ValueError: Test exception" in caplog.text


def test_logger_debug_message(caplog):
    """Test debug logging."""
    logger = Logger("test_module", level="DEBUG")
    
    with caplog.at_level(logging.DEBUG):
        logger.debug("Test debug message")
    
    assert "Test debug message" in caplog.text
    assert "DEBUG" in caplog.text


def test_logger_file_output():
    """Test logger writes to file when log_file is specified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        logger = Logger("test_module", level="INFO", log_file=log_file)
        
        logger.info("Test file logging")
        logger.warning("Test warning")
        logger.error("Test error")
        
        # Close logger to release file handles
        logger.close()
        
        # Verify file was created and contains messages
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert "Test file logging" in content
        assert "Test warning" in content
        assert "Test error" in content
        assert "INFO" in content
        assert "WARNING" in content
        assert "ERROR" in content


def test_logger_file_output_creates_directory():
    """Test logger creates parent directories for log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "subdir" / "nested" / "test.log"
        logger = Logger("test_module", level="INFO", log_file=log_file)
        
        logger.info("Test nested directory")
        
        # Close logger to release file handles
        logger.close()
        
        # Verify directory and file were created
        assert log_file.parent.exists()
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert "Test nested directory" in content


def test_logger_dual_output():
    """Test logger outputs to both console and file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        logger = Logger("test_module", level="INFO", log_file=log_file)
        
        # Check that logger has 2 handlers (console + file)
        assert len(logger.logger.handlers) == 2
        
        # Verify one is StreamHandler and one is FileHandler
        handler_types = [type(h).__name__ for h in logger.logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types
        
        # Close logger to release file handles
        logger.close()


def test_logger_level_filtering():
    """Test logger filters messages based on level."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        logger = Logger("test_module", level="WARNING", log_file=log_file)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Close logger to release file handles
        logger.close()
        
        content = log_file.read_text(encoding='utf-8')
        
        # DEBUG and INFO should be filtered out
        assert "Debug message" not in content
        assert "Info message" not in content
        
        # WARNING and ERROR should be present
        assert "Warning message" in content
        assert "Error message" in content


def test_logger_format():
    """Test logger uses correct format: [时间] [级别] [模块] 消息."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        logger = Logger("test_module", level="INFO", log_file=log_file)
        
        logger.info("Test message")
        
        # Close logger to release file handles
        logger.close()
        
        content = log_file.read_text(encoding='utf-8')
        
        # Check format components
        assert "[INFO]" in content
        assert "[test_module]" in content
        assert "Test message" in content
        
        # Check timestamp format (YYYY-MM-DD HH:MM:SS)
        import re
        timestamp_pattern = r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]'
        assert re.search(timestamp_pattern, content)
