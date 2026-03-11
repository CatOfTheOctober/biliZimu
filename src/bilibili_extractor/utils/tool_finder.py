"""工具路径查找器。

自动查找BBDown和FFmpeg等外部工具的路径。
优先使用项目内的tools目录，然后查找系统PATH。
"""

import os
import shutil
from pathlib import Path
from typing import Optional
import logging


class ToolFinder:
    """外部工具路径查找器。"""
    
    def __init__(self):
        """初始化工具查找器。"""
        self.logger = logging.getLogger(__name__)
        self._project_root = self._find_project_root()
    
    def _find_project_root(self) -> Path:
        """查找项目根目录。
        
        从当前工作目录向上查找，直到找到包含 pyproject.toml 的目录。
        
        Returns:
            项目根目录路径
        """
        current = Path.cwd()
        
        # 向上查找最多5层
        for _ in range(5):
            # 检查是否是项目根目录
            if (current / "pyproject.toml").exists():
                self.logger.debug(f"Found project root: {current}")
                return current
            
            # 向上一层
            if current.parent == current:
                break
            current = current.parent
        
        # 如果没找到，返回当前工作目录
        self.logger.debug(f"Project root not found, using cwd: {Path.cwd()}")
        return Path.cwd()
    
    def find_bbdown(self, config_path: Optional[str] = None) -> Optional[Path]:
        """查找BBDown可执行文件。
        
        查找顺序：
        1. 配置文件中指定的路径
        2. 项目tools/BBDown/BBDown.exe
        3. 环境变量BBDOWN_DIR
        4. 系统PATH
        
        Args:
            config_path: 配置文件中指定的路径
            
        Returns:
            BBDown可执行文件路径，如果未找到返回None
        """
        search_paths = []
        
        # 1. 配置文件中指定的路径
        if config_path:
            config_path_obj = Path(config_path)
            if not config_path_obj.is_absolute():
                # 相对路径，相对于项目根目录
                config_path_obj = self._project_root / config_path
            search_paths.append(config_path_obj)
        
        # 2. 项目tools目录
        project_bbdown = self._project_root / "tools" / "BBDown" / "BBDown.exe"
        search_paths.append(project_bbdown)
        
        # 3. 环境变量
        bbdown_dir = os.environ.get('BBDOWN_DIR')
        if bbdown_dir:
            search_paths.append(Path(bbdown_dir) / "BBDown.exe")
        
        # 4. 系统PATH
        bbdown_in_path = shutil.which('BBDown')
        if bbdown_in_path:
            search_paths.append(Path(bbdown_in_path))
        
        # 搜索
        for path in search_paths:
            if path.exists() and path.is_file():
                self.logger.info(f"Found BBDown at: {path}")
                return path
        
        self.logger.warning("BBDown not found in any search paths")
        return None
    
    def find_ffmpeg(self, config_path: Optional[str] = None) -> Optional[Path]:
        """查找FFmpeg可执行文件。
        
        查找顺序：
        1. 配置文件中指定的路径
        2. 项目tools/ffmpeg/bin/ffmpeg.exe
        3. 系统PATH
        
        Args:
            config_path: 配置文件中指定的路径
            
        Returns:
            FFmpeg可执行文件路径，如果未找到返回None
        """
        search_paths = []
        
        # 1. 配置文件中指定的路径
        if config_path:
            config_path_obj = Path(config_path)
            if not config_path_obj.is_absolute():
                config_path_obj = self._project_root / config_path
            search_paths.append(config_path_obj)
        
        # 2. 项目tools目录
        project_ffmpeg = self._project_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
        search_paths.append(project_ffmpeg)
        
        # 3. 系统PATH
        ffmpeg_in_path = shutil.which('ffmpeg')
        if ffmpeg_in_path:
            search_paths.append(Path(ffmpeg_in_path))
        
        # 搜索
        for path in search_paths:
            if path.exists() and path.is_file():
                self.logger.info(f"Found FFmpeg at: {path}")
                return path
        
        self.logger.warning("FFmpeg not found in any search paths")
        return None
    
    def find_ffprobe(self, config_path: Optional[str] = None) -> Optional[Path]:
        """查找FFprobe可执行文件。
        
        查找顺序：
        1. 配置文件中指定的路径
        2. 项目tools/ffmpeg/bin/ffprobe.exe
        3. 系统PATH
        
        Args:
            config_path: 配置文件中指定的路径
            
        Returns:
            FFprobe可执行文件路径，如果未找到返回None
        """
        search_paths = []
        
        # 1. 配置文件中指定的路径
        if config_path:
            config_path_obj = Path(config_path)
            if not config_path_obj.is_absolute():
                config_path_obj = self._project_root / config_path
            search_paths.append(config_path_obj)
        
        # 2. 项目tools目录
        project_ffprobe = self._project_root / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
        search_paths.append(project_ffprobe)
        
        # 3. 系统PATH
        ffprobe_in_path = shutil.which('ffprobe')
        if ffprobe_in_path:
            search_paths.append(Path(ffprobe_in_path))
        
        # 搜索
        for path in search_paths:
            if path.exists() and path.is_file():
                self.logger.info(f"Found FFprobe at: {path}")
                return path
        
        self.logger.warning("FFprobe not found in any search paths")
        return None
    
    def get_project_root(self) -> Path:
        """获取项目根目录。
        
        Returns:
            项目根目录路径
        """
        return self._project_root
