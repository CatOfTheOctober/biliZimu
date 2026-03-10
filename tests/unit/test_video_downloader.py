"""Unit tests for VideoDownloader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from bilibili_extractor.modules.video_downloader import VideoDownloader, DownloadError
from bilibili_extractor.core.config import Config


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        temp_dir="./test_temp",
        video_quality="720P",
        download_threads=4,
        cookie_file=None
    )


@pytest.fixture
def downloader(config):
    """Create a VideoDownloader instance."""
    return VideoDownloader(config)


class TestVideoDownloaderInit:
    """Test VideoDownloader initialization."""

    def test_init_with_config(self, config):
        """Test initialization with config."""
        downloader = VideoDownloader(config)
        assert downloader.config == config


class TestVideoDownloaderDownload:
    """Test VideoDownloader.download() method."""

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_download_success(self, mock_glob, mock_mkdir, mock_popen, downloader):
        """Test successful video download."""
        # Mock subprocess output
        mock_process = MagicMock()
        mock_process.stdout = [
            "开始下载...\n",
            "下载进度: 25.5%\n",
            "下载进度: 50.0%\n",
            "下载进度: 75.3%\n",
            "下载进度: 100.0%\n",
            "下载完成\n"
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Download video
        result = downloader.download("BV1xx411c7mD")
        
        # Verify result
        assert result == mock_video_file
        
        # Verify BBDown command was called
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "BBDown"
        assert "https://www.bilibili.com/video/BV1xx411c7mD" in call_args
        assert "--work-dir" in call_args
        assert "-q" in call_args
        assert "64" in call_args  # 720P quality code

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_download_with_progress_callback(self, mock_glob, mock_mkdir, mock_popen, downloader):
        """Test download with progress callback."""
        # Mock subprocess output
        mock_process = MagicMock()
        mock_process.stdout = [
            "下载进度: 25.0%\n",
            "下载进度: 50.0%\n",
            "下载进度: 75.0%\n",
            "下载进度: 100.0%\n"
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Create progress callback
        progress_values = []
        def progress_callback(progress):
            progress_values.append(progress)
        
        # Download video
        downloader.download("BV1xx411c7mD", progress_callback)
        
        # Verify progress callback was called with increasing values
        assert len(progress_values) >= 4
        assert progress_values[0] == 25.0
        assert progress_values[1] == 50.0
        assert progress_values[2] == 75.0
        assert progress_values[3] == 100.0

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    def test_download_bbdown_not_found(self, mock_mkdir, mock_popen, downloader):
        """Test download when BBDown is not installed."""
        mock_popen.side_effect = FileNotFoundError()
        
        with pytest.raises(FileNotFoundError) as exc_info:
            downloader.download("BV1xx411c7mD")
        
        assert "BBDown not found" in str(exc_info.value)

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    def test_download_bbdown_fails(self, mock_mkdir, mock_popen, downloader):
        """Test download when BBDown command fails."""
        # Mock subprocess failure
        mock_process = MagicMock()
        mock_process.stdout = ["错误: 视频不存在\n"]
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        
        with pytest.raises(DownloadError) as exc_info:
            downloader.download("BV1xx411c7mD")
        
        assert "BBDown failed" in str(exc_info.value)

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_download_video_file_not_found(self, mock_glob, mock_mkdir, mock_popen, downloader):
        """Test download when video file is not found after download."""
        # Mock subprocess success
        mock_process = MagicMock()
        mock_process.stdout = ["下载完成\n"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock no video files found
        mock_glob.return_value = []
        
        with pytest.raises(DownloadError) as exc_info:
            downloader.download("BV1xx411c7mD")
        
        assert "Video file not found" in str(exc_info.value)


class TestVideoDownloaderCommandConstruction:
    """Test BBDown command construction."""

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_command_with_cookie_file(self, mock_glob, mock_mkdir, mock_popen):
        """Test command construction with cookie file."""
        config = Config(
            temp_dir="./test_temp",
            video_quality="720P",
            cookie_file="/path/to/cookie.txt"
        )
        downloader = VideoDownloader(config)
        
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.stdout = ["下载完成\n"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Download
        downloader.download("BV1xx411c7mD")
        
        # Verify cookie parameter
        call_args = mock_popen.call_args[0][0]
        assert "--cookie" in call_args
        assert "/path/to/cookie.txt" in call_args

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_command_with_quality_1080p(self, mock_glob, mock_mkdir, mock_popen):
        """Test command construction with 1080P quality."""
        config = Config(
            temp_dir="./test_temp",
            video_quality="1080P"
        )
        downloader = VideoDownloader(config)
        
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.stdout = ["下载完成\n"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Download
        downloader.download("BV1xx411c7mD")
        
        # Verify quality parameter
        call_args = mock_popen.call_args[0][0]
        assert "-q" in call_args
        assert "80" in call_args  # 1080P quality code

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_command_with_multi_threading(self, mock_glob, mock_mkdir, mock_popen):
        """Test command construction with multi-threading."""
        config = Config(
            temp_dir="./test_temp",
            download_threads=8
        )
        downloader = VideoDownloader(config)
        
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.stdout = ["下载完成\n"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Download
        downloader.download("BV1xx411c7mD")
        
        # Verify multi-threading parameter (BBDown -mt flag doesn't take a value)
        call_args = mock_popen.call_args[0][0]
        assert "-mt" in call_args


class TestVideoDownloaderProgressParsing:
    """Test progress parsing from BBDown output."""

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_parse_progress_percentage(self, mock_glob, mock_mkdir, mock_popen, downloader):
        """Test parsing progress percentage from output."""
        # Mock subprocess output with various progress formats
        mock_process = MagicMock()
        mock_process.stdout = [
            "Progress: 10%\n",
            "下载进度: 20.5%\n",
            "Some other text\n",
            "Progress: 45.75%\n",
            "下载进度: 100%\n"
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Create progress callback
        progress_values = []
        def progress_callback(progress):
            progress_values.append(progress)
        
        # Download
        downloader.download("BV1xx411c7mD", progress_callback)
        
        # Verify progress values were parsed correctly
        assert 10.0 in progress_values
        assert 20.5 in progress_values
        assert 45.75 in progress_values
        assert 100.0 in progress_values

    @patch('bilibili_extractor.modules.video_downloader.subprocess.Popen')
    @patch('bilibili_extractor.modules.video_downloader.Path.mkdir')
    @patch('bilibili_extractor.modules.video_downloader.Path.glob')
    def test_progress_monotonic_increase(self, mock_glob, mock_mkdir, mock_popen, downloader):
        """Test that progress callback is only called with increasing values."""
        # Mock subprocess output with non-monotonic progress
        mock_process = MagicMock()
        mock_process.stdout = [
            "Progress: 30%\n",
            "Progress: 25%\n",  # Decrease (should be ignored)
            "Progress: 40%\n",
            "Progress: 35%\n",  # Decrease (should be ignored)
            "Progress: 50%\n"
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.stat.return_value.st_mtime = 1234567890
        mock_glob.return_value = [mock_video_file]
        
        # Create progress callback
        progress_values = []
        def progress_callback(progress):
            progress_values.append(progress)
        
        # Download
        downloader.download("BV1xx411c7mD", progress_callback)
        
        # Verify only increasing values were reported
        assert progress_values == [30.0, 40.0, 50.0, 100.0]


class TestVideoDownloaderFindVideoFile:
    """Test _find_video_file() method."""

    def test_find_video_file_with_video_id(self, downloader, tmp_path):
        """Test finding video file with video ID in filename."""
        # Create test video file
        video_file = tmp_path / "BV1xx411c7mD.mp4"
        video_file.touch()
        
        # Find video file
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        
        assert result == video_file

    def test_find_video_file_without_video_id(self, downloader, tmp_path):
        """Test finding video file without video ID in filename."""
        # Create test video file
        video_file = tmp_path / "video.mp4"
        video_file.touch()
        
        # Find video file
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        
        assert result == video_file

    def test_find_video_file_multiple_files(self, downloader, tmp_path):
        """Test finding most recent video file when multiple exist."""
        import time
        
        # Create multiple video files
        old_file = tmp_path / "old_video.mp4"
        old_file.touch()
        time.sleep(0.01)
        
        new_file = tmp_path / "new_video.mp4"
        new_file.touch()
        
        # Find video file (should return most recent)
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        
        assert result == new_file

    def test_find_video_file_not_found(self, downloader, tmp_path):
        """Test finding video file when none exist."""
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        
        assert result is None

    def test_find_video_file_different_extensions(self, downloader, tmp_path):
        """Test finding video files with different extensions."""
        # Test .mp4
        mp4_file = tmp_path / "video.mp4"
        mp4_file.touch()
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        assert result == mp4_file
        mp4_file.unlink()
        
        # Test .flv
        flv_file = tmp_path / "video.flv"
        flv_file.touch()
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        assert result == flv_file
        flv_file.unlink()
        
        # Test .mkv
        mkv_file = tmp_path / "video.mkv"
        mkv_file.touch()
        result = downloader._find_video_file(tmp_path, "BV1xx411c7mD")
        assert result == mkv_file
