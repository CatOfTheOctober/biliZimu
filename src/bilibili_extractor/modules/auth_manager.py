"""Cookie管理和BBDown登录集成模块。"""

import os
import logging
from pathlib import Path
from typing import Optional
from ..core.config import Config
from ..utils.tool_finder import ToolFinder


class AuthManager:
    """管理B站Cookie和BBDown登录。
    
    负责：
    1. 检测BBDown Cookie文件位置
    2. 读取和验证Cookie内容
    3. 集成BBDown登录功能
    """
    
    def __init__(self, config: Config):
        """初始化AuthManager。
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._cookie_path: Optional[Path] = None
        self._tool_finder = ToolFinder()
    
    def get_bbdown_cookie_path(self, login_type: str = 'web') -> Optional[Path]:
        """查找BBDown Cookie文件位置。
        
        BBDown将Cookie保存在BBDown.exe同目录下：
        - Web登录: BBDown.data
        - TV登录: BBDownTV.data
        
        Args:
            login_type: 登录类型，'web'或'tv'
            
        Returns:
            Cookie文件路径，如果不存在返回None
        """
        # 确定Cookie文件名
        cookie_filename = "BBDown.data" if login_type == 'web' else "BBDownTV.data"
        
        # 搜索路径列表
        search_paths = []
        
        # 1. 环境变量指定的BBDown目录
        bbdown_dir = os.environ.get('BBDOWN_DIR')
        if bbdown_dir:
            search_paths.append(Path(bbdown_dir) / cookie_filename)
        
        # 2. 项目tools目录（优先级最高）
        project_root = self._tool_finder.get_project_root()
        project_cookie = project_root / "tools" / "BBDown" / cookie_filename
        search_paths.insert(0, project_cookie)  # 插入到最前面
        
        # 3. BBDown.exe所在目录
        bbdown_exe = self._tool_finder.find_bbdown(self.config.bbdown_path)
        if bbdown_exe:
            bbdown_dir_path = bbdown_exe.parent
            search_paths.append(bbdown_dir_path / cookie_filename)
            self.logger.debug(f"Found BBDown.exe at: {bbdown_dir_path}")
        
        # 4. 当前工作目录（向后兼容）
        search_paths.append(Path.cwd() / cookie_filename)
        
        # 5. 系统常见位置
        if os.name == 'nt':
            # Windows常见位置
            user_home = Path.home()
            search_paths.extend([
                user_home / "BBDown" / cookie_filename,
                user_home / ".bbdown" / cookie_filename,
            ])
        else:
            # Linux/Mac常见位置
            user_home = Path.home()
            search_paths.extend([
                user_home / ".bbdown" / cookie_filename,
                user_home / "BBDown" / cookie_filename,
            ])
        
        # 搜索Cookie文件
        for path in search_paths:
            if path.exists() and path.is_file():
                self.logger.debug(f"Found BBDown cookie file: {path}")
                return path
        
        self.logger.debug(f"BBDown cookie file not found in search paths")
        return None
    
    def check_cookie(self, login_type: str = 'web') -> bool:
        """检查Cookie文件是否存在。
        
        Args:
            login_type: 登录类型，'web'或'tv'
            
        Returns:
            如果Cookie文件存在返回True，否则返回False
        """
        # 如果用户指定了cookie_file，优先使用
        if self.config.cookie_file:
            cookie_path = Path(self.config.cookie_file)
            if cookie_path.exists() and cookie_path.is_file():
                self._cookie_path = cookie_path
                self.logger.info(f"Using custom cookie file: {cookie_path}")
                return True
            else:
                self.logger.warning(f"Custom cookie file not found: {cookie_path}")
                return False
        
        # 否则查找BBDown的Cookie文件
        cookie_path = self.get_bbdown_cookie_path(login_type)
        if cookie_path:
            self._cookie_path = cookie_path
            return True
        
        return False
    
    def get_cookie_path(self) -> Optional[Path]:
        """获取Cookie文件路径。
        
        Returns:
            Cookie文件路径，如果未找到返回None
        """
        return self._cookie_path
    
    def read_cookie_content(self, cookie_path: Path) -> str:
        """读取Cookie文件内容。
        
        BBDown保存的Cookie格式：
        - 字段用分号分隔：SESSDATA=xxx;bili_jct=xxx;DedeUserID=xxx
        - 英文逗号被转义为%2C，需要转回来
        
        Args:
            cookie_path: Cookie文件路径
            
        Returns:
            Cookie内容字符串
            
        Raises:
            IOError: 读取文件失败
        """
        try:
            with open(cookie_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 将%2C转义还原为逗号
            content = content.replace('%2C', ',')
            
            self.logger.debug(f"Successfully read cookie from {cookie_path}")
            return content
        except Exception as e:
            self.logger.error(f"Failed to read cookie file {cookie_path}: {e}")
            raise IOError(f"Failed to read cookie file: {e}")
    
    def validate_cookie_format(self, cookie_path: Path, login_type: str = 'web') -> bool:
        """验证Cookie格式是否有效。
        
        Web登录Cookie必须包含SESSDATA字段。
        TV登录Cookie必须包含access_token字段。
        
        Args:
            cookie_path: Cookie文件路径
            login_type: 登录类型，'web'或'tv'
            
        Returns:
            如果Cookie格式有效返回True，否则返回False
        """
        try:
            content = self.read_cookie_content(cookie_path)
            
            # 检查必需字段
            if login_type == 'web':
                # Web登录需要SESSDATA
                if 'SESSDATA=' not in content:
                    self.logger.warning(f"Cookie file missing SESSDATA field: {cookie_path}")
                    return False
            else:
                # TV登录需要access_token
                if 'access_token=' not in content:
                    self.logger.warning(f"Cookie file missing access_token field: {cookie_path}")
                    return False
            
            self.logger.debug(f"Cookie format validation passed: {cookie_path}")
            return True
        except Exception as e:
            self.logger.error(f"Cookie validation failed: {e}")
            return False

    def save_cookie_securely(self, cookie_path: Path, content: str) -> None:
        """安全地保存Cookie到文件。
        
        在Unix系统设置文件权限为600（仅所有者可读写）。
        在Windows系统使用适当的权限设置。
        
        Args:
            cookie_path: Cookie文件路径
            content: Cookie内容
            
        Raises:
            IOError: 保存失败
        """
        try:
            # 写入文件
            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 设置文件权限
            if os.name != 'nt':  # Unix/Linux/Mac
                os.chmod(cookie_path, 0o600)
                self.logger.info(f"Cookie saved with secure permissions (600): {cookie_path}")
            else:  # Windows
                # Windows使用不同的权限系统，这里只记录日志
                self.logger.info(f"Cookie saved: {cookie_path}")
            
            # 记录安全日志（不输出Cookie内容）
            self.logger.debug(f"Cookie file saved securely to {cookie_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save cookie securely: {e}")
            raise IOError(f"Failed to save cookie: {e}")


    def login_with_bbdown(self, login_type: str = 'web') -> None:
        """使用BBDown进行登录。

        调用BBDown的登录功能，支持Web扫码登录和TV登录。

        Args:
            login_type: 登录类型，'web'或'tv'

        Raises:
            AuthenticationError: 登录失败
        """
        import subprocess
        from ..core.exceptions import AuthenticationError

        try:
            # 构建BBDown登录命令
            if login_type == 'web':
                # Web扫码登录
                cmd = ['BBDown', 'login']
                print("\n请使用手机B站APP扫描二维码登录...")
            else:
                # TV登录
                cmd = ['BBDown', 'logintv']
                print("\n请使用手机B站APP扫描二维码登录（TV模式）...")

            # 执行BBDown登录
            result = subprocess.run(
                cmd,
                capture_output=False,  # 让用户看到二维码
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                raise AuthenticationError(f"BBDown login failed with exit code {result.returncode}")

            # 验证登录是否成功（检查Cookie文件）
            cookie_path = self.get_bbdown_cookie_path(login_type)
            if not cookie_path or not cookie_path.exists():
                raise AuthenticationError("Login completed but cookie file not found")

            # 验证Cookie格式
            if not self.validate_cookie_format(cookie_path, login_type):
                raise AuthenticationError("Login completed but cookie format is invalid")

            self._cookie_path = cookie_path
            self.logger.info(f"Login successful, cookie saved to: {cookie_path}")

        except subprocess.TimeoutExpired:
            raise AuthenticationError("Login timeout (5 minutes)")
        except FileNotFoundError:
            raise AuthenticationError(
                "BBDown not found. Please install BBDown and add it to PATH.\n"
                "Download: https://github.com/nilaoda/BBDown/releases"
            )
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}")


    def login_with_bbdown(self, login_type: str = 'web') -> None:
        """使用BBDown进行登录。
        
        调用BBDown的登录功能，支持Web扫码登录和TV登录。
        
        Args:
            login_type: 登录类型，'web'或'tv'
            
        Raises:
            AuthenticationError: 登录失败
        """
        import subprocess
        from ..core.exceptions import AuthenticationError
        
        try:
            # 查找BBDown可执行文件
            bbdown_path = self._tool_finder.find_bbdown(self.config.bbdown_path)
            
            if not bbdown_path:
                raise AuthenticationError(
                    "BBDown not found. Please:\n"
                    "1. Place BBDown.exe in tools/BBDown/ directory, or\n"
                    "2. Add BBDown to system PATH, or\n"
                    "3. Set bbdown_path in config file\n"
                    "Download: https://github.com/nilaoda/BBDown/releases"
                )
            
            # 构建BBDown登录命令
            if login_type == 'web':
                # Web扫码登录
                cmd = [str(bbdown_path), 'login']
                print("\n请使用手机B站APP扫描二维码登录...")
            else:
                # TV登录
                cmd = [str(bbdown_path), 'logintv']
                print("\n请使用手机B站APP扫描二维码登录（TV模式）...")
            
            # 执行BBDown登录
            result = subprocess.run(
                cmd,
                capture_output=False,  # 让用户看到二维码
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                raise AuthenticationError(f"BBDown login failed with exit code {result.returncode}")
            
            # 验证登录是否成功（检查Cookie文件）
            cookie_path = self.get_bbdown_cookie_path(login_type)
            if not cookie_path or not cookie_path.exists():
                raise AuthenticationError("Login completed but cookie file not found")
            
            # 验证Cookie格式
            if not self.validate_cookie_format(cookie_path, login_type):
                raise AuthenticationError("Login completed but cookie format is invalid")
            
            self._cookie_path = cookie_path
            self.logger.info(f"Login successful, cookie saved to: {cookie_path}")
            
        except subprocess.TimeoutExpired:
            raise AuthenticationError("Login timeout (5 minutes)")
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}")
