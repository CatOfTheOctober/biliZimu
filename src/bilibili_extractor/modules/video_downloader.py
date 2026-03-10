"""Video downloading for Bilibili videos."""

import subprocess
import re
import time
from typing import Optional, Callable
from pathlib import Path
from bilibili_extractor.core.config import Config
from bilibili_extractor.utils.tool_finder import ToolFinder


class DownloadError(Exception):
    """Exception raised when video download fails."""
    pass


class VideoDownloader:
    """Download Bilibili videos using BBDown.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 3.8
    """

    def __init__(self, config: Config):
        """Initialize video downloader.

        Args:
            config: Configuration object
        """
        self.config = config
        
        # Find BBDown executable
        tool_finder = ToolFinder()
        bbdown_path = tool_finder.find_bbdown(config.bbdown_path)
        
        if not bbdown_path:
            raise FileNotFoundError(
                "BBDown not found. Please install BBDown in tools/BBDown/ directory "
                "or add it to your system PATH."
            )
        
        self.bbdown_path = bbdown_path

    def download(self, video_id: str, progress_callback: Optional[Callable] = None) -> Path:
        """Download video file using BBDown.

        Args:
            video_id: Bilibili video ID
            progress_callback: Optional callback for progress updates (receives percentage: float)

        Returns:
            Path to downloaded video file

        Raises:
            DownloadError: If download fails
            FileNotFoundError: If BBDown is not installed
        """
        return self._download_with_bbdown(video_id, progress_callback)

    def _download_with_bbdown(self, video_id: str, progress_callback: Optional[Callable] = None) -> Path:
        """Download video using BBDown command.

        Args:
            video_id: Bilibili video ID
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded video file

        Raises:
            DownloadError: If download fails
            FileNotFoundError: If BBDown is not installed
        """
        # Create temp directory
        temp_dir = Path(self.config.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct video URL
        video_url = f"https://www.bilibili.com/video/{video_id}"
        
        # Construct BBDown command - use found BBDown path
        cmd = [str(self.bbdown_path), video_url, "--work-dir", str(temp_dir)]
        
        # Add quality parameter (Requirement 3.2)
        quality_map = {
            "480P": "32",
            "720P": "64",
            "1080P": "80",
            "1080P60": "116",
            "4K": "120"
        }
        quality_code = quality_map.get(self.config.video_quality, "64")
        cmd.extend(["-q", quality_code])
        
        # Add cookie file if provided (Requirement 3.3)
        if self.config.cookie_file:
            cmd.extend(["--cookie", self.config.cookie_file])
        
        # Add multi-threading parameter (Requirement 3.4)
        # BBDown's -mt flag enables multi-threading (no value needed)
        if self.config.download_threads > 1:
            cmd.append("-mt")
        
        try:
            # Execute BBDown command (Requirement 3.1)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            # Parse output for progress (Requirement 3.5, 3.7)
            last_progress = 0.0
            output_lines = []
            
            for line in process.stdout:
                output_lines.append(line)
                
                # Parse progress from BBDown output
                # BBDown outputs progress like: "下载进度: 45.2%" or "Progress: 45.2%"
                progress_match = re.search(r'(\d+\.?\d*)%', line)
                if progress_match:
                    try:
                        progress = float(progress_match.group(1))
                        # Only call callback if progress increased (monotonic)
                        if progress > last_progress:
                            last_progress = progress
                            if progress_callback:
                                progress_callback(progress)
                    except ValueError:
                        pass
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Check for errors
            if return_code != 0:
                output = ''.join(output_lines)
                raise DownloadError(
                    f"BBDown failed with return code {return_code}. Output: {output}"
                )
            
            # Find downloaded video file (Requirement 3.8)
            video_file = self._find_video_file(temp_dir, video_id)
            
            if not video_file:
                output = ''.join(output_lines)
                raise DownloadError(
                    f"Video file not found after download. Output: {output}"
                )
            
            # Call callback with 100% to indicate completion
            if progress_callback and last_progress < 100.0:
                progress_callback(100.0)
            
            return video_file
            
        except FileNotFoundError:
            raise FileNotFoundError(
                "BBDown not found. Please install BBDown and ensure it's in your PATH."
            )
        except DownloadError:
            raise
        except Exception as e:
            raise DownloadError(f"Error downloading video: {str(e)}")

    def _find_video_file(self, directory: Path, video_id: str) -> Optional[Path]:
        """Find downloaded video file in directory.

        Args:
            directory: Directory to search
            video_id: Video ID to match in filename

        Returns:
            Path to video file, or None if not found
        """
        # Common video extensions
        video_extensions = ['.mp4', '.flv', '.mkv', '.avi']
        
        # Search for video files
        for ext in video_extensions:
            # Try exact match with video_id
            video_files = list(directory.glob(f"*{video_id}*{ext}"))
            if video_files:
                # Return the most recently modified file
                return max(video_files, key=lambda p: p.stat().st_mtime)
            
            # Try any video file with the extension
            video_files = list(directory.glob(f"*{ext}"))
            if video_files:
                # Return the most recently modified file
                return max(video_files, key=lambda p: p.stat().st_mtime)
        
        return None
