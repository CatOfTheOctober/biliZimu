"""Resource management and cleanup utilities."""

import logging
import shutil
from typing import List, Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class ResourceManager:
    """Manage temporary files and resource cleanup.
    
    This class provides context manager support to ensure cleanup
    even when exceptions occur.
    
    Example:
        with ResourceManager(temp_dir="./temp") as rm:
            rm.register_file(Path("video.mp4"))
            # ... process files ...
        # Files are automatically cleaned up
    """

    def __init__(self, temp_dir: str, keep_files: bool = False):
        """Initialize resource manager.

        Args:
            temp_dir: Temporary directory path
            keep_files: Whether to keep temporary files
        """
        self.temp_dir = Path(temp_dir)
        self.keep_files = keep_files
        self.tracked_files: List[Path] = []

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup resources.
        
        Cleanup is performed regardless of whether an exception occurred.
        """
        self.cleanup()
        return False  # Don't suppress exceptions

    def register_file(self, file_path: Path) -> None:
        """Register a file for cleanup.

        Args:
            file_path: Path to file to track
        """
        if file_path not in self.tracked_files:
            self.tracked_files.append(file_path)
            logger.debug(f"Registered file for cleanup: {file_path}")

    def cleanup(self) -> None:
        """Clean up all tracked temporary files.
        
        This method is idempotent - it can be called multiple times safely.
        Cleanup failures are logged but do not raise exceptions to avoid
        blocking program execution.
        """
        if self.keep_files:
            logger.info(f"Keeping {len(self.tracked_files)} temporary files (keep_files=True)")
            return

        if not self.tracked_files:
            logger.debug("No files to clean up")
            return

        logger.info(f"Cleaning up {len(self.tracked_files)} temporary files")
        
        for file_path in self.tracked_files:
            try:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"Deleted file: {file_path}")
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        logger.debug(f"Deleted directory: {file_path}")
                else:
                    logger.debug(f"File already deleted: {file_path}")
            except Exception as e:
                # Log cleanup failures but don't raise exceptions
                logger.warning(f"Failed to delete {file_path}: {e}")

        # Clear the list after cleanup attempt
        self.tracked_files.clear()

    def check_disk_space(self, required_mb: int) -> bool:
        """Check if sufficient disk space is available.

        Args:
            required_mb: Required space in megabytes

        Returns:
            True if sufficient space available, False otherwise
        """
        try:
            # Get disk usage statistics for the temp directory
            stat = shutil.disk_usage(self.temp_dir)
            available_mb = stat.free / (1024 * 1024)
            
            logger.debug(f"Available disk space: {available_mb:.2f} MB, Required: {required_mb} MB")
            
            return available_mb >= required_mb
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            # Return True to allow operation to proceed if check fails
            return True
