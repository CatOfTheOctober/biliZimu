"""Subtitle fetching and parsing for Bilibili videos."""

import subprocess
import tempfile
import re
import json
import xml.etree.ElementTree as ET
import logging
import time
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.models import TextSegment
from bilibili_extractor.core.exceptions import SubtitleNotFoundError, SubtitleMismatchError, RiskControlError
from .bilibili_api import BilibiliAPI
from .subtitle_parser import SubtitleParser


class SubtitleFetcher:
    """Fetch and parse Bilibili video subtitles."""

    def __init__(self, config: Config):
        """Initialize subtitle fetcher.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.bilibili_api: Optional[BilibiliAPI] = None
    
    def set_cookie(self, cookie: str):
        """设置Cookie并初始化BilibiliAPI。
        
        每次调用都会创建新的BilibiliAPI实例，自动清除旧缓存。
        
        Args:
            cookie: Cookie字符串
        """
        self.bilibili_api = BilibiliAPI(cookie, self.config)
        self.logger.debug("BilibiliAPI initialized with cookie (new instance, fresh cache)")
    
    def _validate_subtitle(self, subtitle_data: Dict[str, Any], expected_aid: int, expected_cid: int) -> None:
        """验证字幕数据是否与请求的视频匹配。
        
        Args:
            subtitle_data: 字幕数据字典
            expected_aid: 期望的 aid
            expected_cid: 期望的 cid
            
        Raises:
            SubtitleMismatchError: 如果 aid 或 cid 不匹配
        """
        # 检查字幕数据是否包含 aid 和 cid 字段
        if 'aid' not in subtitle_data or 'cid' not in subtitle_data:
            self.logger.warning("字幕数据缺少 aid/cid 信息，无法验证匹配性")
            return
        
        returned_aid = subtitle_data.get('aid')
        returned_cid = subtitle_data.get('cid')
        
        # 验证 aid 和 cid 是否匹配
        if returned_aid != expected_aid or returned_cid != expected_cid:
            self.logger.warning(
                f"字幕与视频不匹配: 请求的 aid={expected_aid}, cid={expected_cid}, "
                f"返回的 aid={returned_aid}, cid={returned_cid}"
            )
            raise SubtitleMismatchError(
                message=f"字幕与视频不匹配: 请求的 aid={expected_aid}, cid={expected_cid}, "
                       f"返回的 aid={returned_aid}, cid={returned_cid}",
                requested_aid=expected_aid,
                requested_cid=expected_cid,
                returned_aid=returned_aid,
                returned_cid=returned_cid
            )
        
        # 额外验证：检查字幕内容是否为空
        body = subtitle_data.get('body', [])
        if not body or len(body) == 0:
            self.logger.warning(f"字幕内容为空: aid={returned_aid}, cid={returned_cid}")
            raise SubtitleMismatchError(
                message=f"字幕内容为空: aid={returned_aid}, cid={returned_cid}",
                requested_aid=expected_aid,
                requested_cid=expected_cid,
                returned_aid=returned_aid,
                returned_cid=returned_cid
            )
        
        self.logger.debug(f"字幕验证通过: aid={expected_aid}, cid={expected_cid}, 字幕段数={len(body)}")
    
    def _retry_with_wait(self, func: Callable, max_attempts: int, wait_time: int, *args, **kwargs) -> Any:
        """实现带等待的重试机制。
        
        Args:
            func: 要重试的函数
            max_attempts: 最大重试次数
            wait_time: 每次重试的等待时间（秒）
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            RiskControlError: 如果所有重试都失败，重新抛出最后一个异常
        """
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except RiskControlError as e:
                last_exception = e
                
                if attempt < max_attempts:
                    # 记录警告日志
                    self.logger.warning(f"WBI API 触发风控（412），等待 {wait_time} 秒后重试...")
                    
                    # 实现倒计时等待
                    remaining_time = wait_time
                    while remaining_time > 0:
                        sleep_time = min(5, remaining_time)  # 每5秒输出一次日志
                        time.sleep(sleep_time)
                        remaining_time -= sleep_time
                        if remaining_time > 0:
                            self.logger.info(f"等待中... 剩余 {remaining_time} 秒")
                    
                    # 重试前记录日志
                    self.logger.info(f"正在进行第 {attempt} 次重试（WBI API）...")
                else:
                    # 所有重试都失败
                    self.logger.info(f"WBI API 重试 {max_attempts} 次后仍失败")
                    raise last_exception
        
        # 理论上不会执行到这里，但为了类型安全
        raise last_exception
    
    def _fetch_from_wbi_api(self, aid: int, cid: int) -> Optional[List[TextSegment]]:
        """使用 WBI API 获取字幕，支持重试机制。
        
        Args:
            aid: 视频 aid
            cid: 视频 cid
            
        Returns:
            TextSegment 列表，如果获取失败返回 None
        """
        if not self.bilibili_api:
            self.logger.warning("BilibiliAPI 未初始化，无法使用 WBI API")
            return None
        
        try:
            self.logger.info("正在使用 WBI API 获取字幕")
            
            # 从配置中读取重试参数
            max_attempts = self.config.api_retry_max_attempts
            wait_time = self.config.api_retry_wait_time
            
            # 使用重试机制调用 WBI API
            player_info = self._retry_with_wait(
                self.bilibili_api.get_player_info,
                max_attempts,
                wait_time,
                aid,
                cid
            )
            
            # 提取字幕列表
            subtitles = player_info.get('subtitles', [])
            
            if not subtitles:
                self.logger.info("WBI API 返回的字幕列表为空")
                return None
            
            # 选择字幕（优先 AI 字幕，其次中文字幕）
            selected_subtitle = None
            ai_subtitle = None
            regular_subtitle = None
            
            for subtitle in subtitles:
                lan = subtitle.get('lan', '')
                subtitle_url = subtitle.get('subtitle_url', '')
                
                if lan.startswith('ai-'):
                    ai_subtitle = subtitle
                    self.logger.debug(f"找到 AI 字幕: {lan}")
                    
                    # 如果 AI 字幕 URL 为空，尝试从 AI 字幕 API 获取
                    if not subtitle_url:
                        self.logger.info("AI 字幕 URL 为空，尝试从 AI 字幕 API 获取")
                        subtitle_url = self.bilibili_api.get_ai_subtitle_url(aid, cid)
                        if subtitle_url:
                            subtitle['subtitle_url'] = subtitle_url
                    
                    break
                elif lan in ['zh-CN', 'zh-Hans', 'zh']:
                    regular_subtitle = subtitle
                    self.logger.debug(f"找到普通中文字幕: {lan}")
            
            # 选择字幕（优先 AI 字幕）
            selected_subtitle = ai_subtitle or regular_subtitle
            
            if not selected_subtitle:
                self.logger.info("未找到中文字幕")
                return None
            
            subtitle_url = selected_subtitle.get('subtitle_url')
            if not subtitle_url:
                self.logger.info("字幕 URL 为空")
                return None
            
            # 下载并解析字幕
            self.logger.info(f"下载字幕: {subtitle_url}")
            subtitle_data = self.bilibili_api.download_subtitle(subtitle_url)
            
            # 使用 SubtitleParser 解析字幕
            segments = SubtitleParser.parse_subtitle(subtitle_data)
            
            self.logger.info("WBI API 重试成功，已获取字幕")
            return segments
            
        except RiskControlError as e:
            # RiskControlError 已经在 _retry_with_wait 中处理，这里捕获并记录
            self.logger.warning(f"WBI API 触发风控，所有重试失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"WBI API 获取字幕失败: {e}")
            return None
    
    def _fetch_from_v2_api(self, aid: int, cid: int) -> Optional[List[TextSegment]]:
        """使用 V2 API 获取字幕（降级方案）。
        
        Args:
            aid: 视频 aid
            cid: 视频 cid
            
        Returns:
            TextSegment 列表，如果获取失败返回 None
        """
        if not self.bilibili_api:
            self.logger.warning("BilibiliAPI 未初始化，无法使用 V2 API")
            return None
        
        try:
            self.logger.info("正在使用 V2 API 获取字幕")
            
            # 构造 V2 API 请求 URL
            url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
            
            # 发送请求
            response = self.bilibili_api.session.get(url, timeout=self.bilibili_api.timeout)
            
            # 检查响应状态码
            if response.status_code != 200:
                self.logger.warning(f"V2 API 请求失败，状态码: {response.status_code}")
                return None
            
            # 解析响应数据
            data = response.json()
            
            # 检查 API 返回码
            code = data.get('code')
            if code != 0:
                error_msg = data.get('message', '未知错误')
                self.logger.warning(f"V2 API 返回错误: {error_msg} (code: {code})")
                return None
            
            # 提取字幕列表
            player_data = data.get('data', {})
            subtitle_data = player_data.get('subtitle', {})
            subtitles = subtitle_data.get('subtitles', [])
            
            if not subtitles:
                self.logger.info("V2 API 返回的字幕列表为空")
                return None
            
            # 选择字幕（优先 AI 字幕，其次中文字幕）
            selected_subtitle = None
            ai_subtitle = None
            regular_subtitle = None
            
            for subtitle in subtitles:
                lan = subtitle.get('lan', '')
                subtitle_url = subtitle.get('subtitle_url', '')
                
                if lan.startswith('ai-'):
                    ai_subtitle = subtitle
                    self.logger.debug(f"找到 AI 字幕: {lan}")
                    
                    # 如果 AI 字幕 URL 为空，尝试从 AI 字幕 API 获取
                    if not subtitle_url:
                        self.logger.info("AI 字幕 URL 为空，尝试从 AI 字幕 API 获取")
                        subtitle_url = self.bilibili_api.get_ai_subtitle_url(aid, cid)
                        if subtitle_url:
                            subtitle['subtitle_url'] = subtitle_url
                    
                    break
                elif lan in ['zh-CN', 'zh-Hans', 'zh']:
                    regular_subtitle = subtitle
                    self.logger.debug(f"找到普通中文字幕: {lan}")
            
            # 选择字幕（优先 AI 字幕）
            selected_subtitle = ai_subtitle or regular_subtitle
            
            if not selected_subtitle:
                self.logger.info("未找到中文字幕")
                return None
            
            subtitle_url = selected_subtitle.get('subtitle_url')
            if not subtitle_url:
                self.logger.info("字幕 URL 为空")
                return None
            
            # 下载字幕
            self.logger.info(f"下载字幕: {subtitle_url}")
            subtitle_json = self.bilibili_api.download_subtitle(subtitle_url)
            
            # 验证字幕的 aid/cid 是否匹配
            # 注意：V2 API 返回的字幕数据应该包含 aid 和 cid 信息
            # 如果缺少这些字段，说明字幕数据可能不完整或来自其他视频
            try:
                self._validate_subtitle(subtitle_json, aid, cid)
            except SubtitleMismatchError as e:
                self.logger.warning(f"V2 API 返回的字幕与视频不匹配，降级到 BBDown: {e}")
                return None
            
            # 使用 SubtitleParser 解析字幕
            segments = SubtitleParser.parse_subtitle(subtitle_json)
            
            self.logger.info("V2 API 成功获取字幕")
            return segments
            
        except SubtitleMismatchError as e:
            # 重新抛出，让上层处理
            raise
        except Exception as e:
            self.logger.error(f"V2 API 获取字幕失败: {e}")
            return None
    
    def _fetch_from_bbdown(self, bvid: str) -> Optional[List[TextSegment]]:
        """使用 BBDown 获取字幕（最终降级方案）。
        
        Args:
            bvid: 视频 BVID
            
        Returns:
            TextSegment 列表，如果获取失败返回 None
        """
        try:
            self.logger.info("API 方式失败，使用 BBDown 获取字幕")
            
            # 调用现有的 _download_with_bbdown 方法
            subtitle_files = self._download_with_bbdown(bvid)
            
            if not subtitle_files:
                self.logger.info("BBDown 未找到字幕文件")
                return None
            
            # 获取第一个字幕文件
            subtitle_file = subtitle_files[0]
            
            # 解析字幕文件为 TextSegment 列表
            segments = self.parse_subtitle(subtitle_file)
            
            self.logger.info("BBDown 成功获取字幕")
            return segments
            
        except Exception as e:
            self.logger.error(f"BBDown 获取字幕失败: {e}")
            return None
    
    def fetch_subtitle(self, bvid: str, url: str = "") -> Optional[List[TextSegment]]:
        details = self.fetch_subtitle_details(bvid, url)
        if not details:
            return None
        return details.get("segments")

    def fetch_subtitle_details(self, bvid: str, url: str = "") -> Optional[Dict[str, Any]]:
        """使用 B 站 API 获取字幕（AI 字幕优先）。
        
        完全同步“下载字幕.py”逻辑：
        1. 获取视频信息 (aid, cid)
        2. 调用 get_subtitle_with_ai_fallback 获取字幕内容
        3. 进行 aid/cid 匹配验证
        
        Args:
            bvid: 视频 BVID
            url: 完整视频 URL
            
        Returns:
            包含标准字幕片段、视频元信息和原始字幕数据的字典；失败返回 None
        """
        if not self.bilibili_api:
            self.logger.warning("BilibiliAPI 未初始化")
            return None
        
        try:
            # 1. 获取视频信息 (支持多P)
            from .url_validator import URLValidator
            page = URLValidator.extract_page_number(url) if url else 1
            video_info = self.bilibili_api.get_video_info(bvid, page)
            aid = video_info['aid']
            cid = video_info['cid']
            
            # 2. 直接调用与“下载字幕.py”一致的 API ( Requirement 5.1/5.4 增强)
            self.logger.info(f"正在从 API 获取字幕 (BVID: {bvid}, CID: {cid})")
            result = self.bilibili_api.get_subtitle_with_ai_fallback(bvid, cid)
            
            if not result.get('success'):
                self.logger.info(f"API 字幕获取未成功: {result.get('message')}")
                return None
            
            # 3. 字幕内容解析
            subtitles_data = result.get('subtitles', [])
            if not subtitles_data:
                return None
            
            # 这里的 subtitles_data 已经是 bilibili_api 内部处理过的字典列表
            # 由于 bilibili_api.get_subtitle_with_ai_fallback 内部已经处理了下载
            # 我们只需要将这些 body 里的片段转换成 TextSegment 对象
            from bilibili_extractor.modules.subtitle_parser import SubtitleParser
            segments = SubtitleParser.parse_subtitle({'body': subtitles_data})

            selected_track = {
                "track_id": "selected_subtitle",
                "track_type": "subtitle",
                "source": "platform_ai_subtitle" if result.get("metadata", {}).get("lan", "").startswith("ai-") else "platform_subtitle",
                "label": result.get("metadata", {}).get("lan_doc") or result.get("metadata", {}).get("lan") or "subtitle",
                "language": result.get("metadata", {}).get("lan"),
                "is_ai_generated": result.get("metadata", {}).get("lan", "").startswith("ai-"),
                "available_subtitles": result.get("available_subtitles", []),
            }
            
            self.logger.info(f"成功同步获取 API 字幕，共 {len(segments)} 条片段")
            return {
                "segments": segments,
                "video_info": video_info,
                "subtitle_result": result,
                "selected_track": selected_track,
            }
            
        except Exception as e:
            self.logger.error(f"API 字幕获取失败: {e}")
            return None

    def get_video_metadata(self, bvid: str, url: str = "") -> Optional[Dict[str, Any]]:
        """Fetch normalized page metadata without downloading subtitles."""
        if not self.bilibili_api:
            return None
        try:
            from .url_validator import URLValidator

            page = URLValidator.extract_page_number(url) if url else 1
            return self.bilibili_api.get_video_info(bvid, page)
        except Exception as e:
            self.logger.warning(f"获取视频元信息失败: {e}")
            return None


    def check_subtitle_availability(self, video_id: str) -> bool:
        """Check if video has official subtitles.

        Args:
            video_id: Bilibili video ID

        Returns:
            True if subtitles exist, False otherwise
        """
        try:
            # Try to download subtitles to check availability
            self.download_subtitles(video_id)
            return True
        except SubtitleNotFoundError:
            return False

    def download_subtitles(self, video_id: str) -> List[Path]:
        """Download subtitle files using BBDown.

        Args:
            video_id: Bilibili video ID

        Returns:
            List of paths to downloaded subtitle files

        Raises:
            SubtitleNotFoundError: If no subtitles are found for the video
        """
        return self._download_with_bbdown(video_id)

    def _download_with_bbdown(self, video_id: str) -> List[Path]:
        """Download subtitles using BBDown --sub-only command.

        Args:
            video_id: Bilibili video ID

        Returns:
            List of paths to downloaded subtitle files

        Raises:
            SubtitleNotFoundError: If no subtitles are found
        """
        # Create temporary directory for downloads
        temp_dir = self.config.resolved_temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a unique subdirectory for this download
        with tempfile.TemporaryDirectory(dir=temp_dir) as work_dir:
            work_path = Path(work_dir)
            
            # Construct BBDown command
            video_url = f"https://www.bilibili.com/video/{video_id}"
            cmd = ["BBDown", video_url, "--sub-only", "--work-dir", str(work_path)]
            
            # Add cookie file if provided
            if self.config.cookie_file:
                cmd.extend(["--cookie", self.config.cookie_file])
            
            try:
                # Execute BBDown command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # Check if BBDown reported no subtitles
                output = result.stdout + result.stderr
                
                # Common patterns indicating no subtitles
                no_subtitle_patterns = [
                    r"不存在字幕",
                    r"无字幕",
                    r"no subtitle",
                    r"subtitle.*not.*found",
                    r"字幕.*不存在"
                ]
                
                for pattern in no_subtitle_patterns:
                    if re.search(pattern, output, re.IGNORECASE):
                        raise SubtitleNotFoundError(
                            f"No subtitles found for video {video_id}"
                        )
                
                # Check for command execution errors
                if result.returncode != 0:
                    # If BBDown failed but not due to missing subtitles, raise error
                    raise RuntimeError(
                        f"BBDown command failed with return code {result.returncode}: {output}"
                    )
                
                # Search for downloaded subtitle files
                subtitle_files = self._find_subtitle_files(work_path)
                
                if not subtitle_files:
                    raise SubtitleNotFoundError(
                        f"No subtitle files found after BBDown execution for video {video_id}"
                    )
                
                # Select Chinese subtitle if multiple files exist
                selected_subtitle = self._select_chinese_subtitle(subtitle_files)
                
                # Copy selected subtitle file to temp_dir for persistence
                dest_file = temp_dir / f"{video_id}_{selected_subtitle.name}"
                dest_file.write_bytes(selected_subtitle.read_bytes())
                
                return [dest_file]
                
            except FileNotFoundError:
                raise RuntimeError(
                    "BBDown not found. Please install BBDown and ensure it's in your PATH."
                )
            except SubtitleNotFoundError:
                # Re-raise SubtitleNotFoundError as-is
                raise
            except Exception as e:
                raise RuntimeError(f"Error downloading subtitles: {str(e)}")

    def _find_subtitle_files(self, directory: Path) -> List[Path]:
        """Find subtitle files in the given directory.

        Args:
            directory: Directory to search for subtitle files

        Returns:
            List of paths to subtitle files (SRT, JSON, XML)
        """
        subtitle_extensions = ['.srt', '.json', '.xml']
        subtitle_files = []
        
        for ext in subtitle_extensions:
            subtitle_files.extend(directory.glob(f"*{ext}"))
        
        return subtitle_files
    
    def _select_chinese_subtitle(self, subtitle_files: List[Path]) -> Path:
        """Select Chinese subtitle from multiple subtitle files.

        Prioritizes Chinese subtitles (zh-CN, zh-Hans, zh) over other languages.

        Args:
            subtitle_files: List of subtitle file paths

        Returns:
            Path to the selected subtitle file (Chinese if available, otherwise first file)
        """
        if not subtitle_files:
            raise ValueError("No subtitle files provided")
        
        if len(subtitle_files) == 1:
            return subtitle_files[0]
        
        # Chinese language patterns to look for in filenames
        chinese_patterns = [
            r'zh[-_]?cn',  # zh-CN, zh_CN, zhcn
            r'zh[-_]?hans',  # zh-Hans, zh_Hans, zhhans
            r'[\u4e00-\u9fff]',  # Chinese characters
            r'中文',
            r'简体',
            r'zh(?![-_])',  # zh but not followed by - or _
        ]
        
        # Try to find Chinese subtitle
        for subtitle_file in subtitle_files:
            filename_lower = subtitle_file.name.lower()
            for pattern in chinese_patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return subtitle_file
        
        # If no Chinese subtitle found, return the first one
        return subtitle_files[0]

    def parse_subtitle(self, subtitle_path: Path) -> List[TextSegment]:
        """Parse subtitle file (SRT/JSON/XML).

        Args:
            subtitle_path: Path to subtitle file

        Returns:
            List of TextSegment objects sorted by start_time

        Raises:
            ValueError: If file format is not supported or parsing fails
        """
        if not subtitle_path.exists():
            raise ValueError(f"Subtitle file not found: {subtitle_path}")
        
        # Determine format by extension
        suffix = subtitle_path.suffix.lower()
        
        if suffix == '.srt':
            return self._parse_srt(subtitle_path)
        elif suffix == '.json':
            return self._parse_json(subtitle_path)
        elif suffix == '.xml':
            return self._parse_xml(subtitle_path)
        else:
            raise ValueError(f"Unsupported subtitle format: {suffix}")
    
    def _parse_srt(self, subtitle_path: Path) -> List[TextSegment]:
        """Parse SRT format subtitle file.

        SRT format example:
        1
        00:00:01,000 --> 00:00:03,000
        这是第一句字幕

        Args:
            subtitle_path: Path to SRT file

        Returns:
            List of TextSegment objects
        """
        segments = []
        content = subtitle_path.read_text(encoding='utf-8')
        
        # Split by double newlines to get individual subtitle blocks
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            # Parse timestamp line (line 1, line 0 is the sequence number)
            timestamp_line = lines[1]
            timestamp_match = re.match(
                r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                timestamp_line
            )
            
            if not timestamp_match:
                continue
            
            # Convert timestamp to seconds
            start_h, start_m, start_s, start_ms = map(int, timestamp_match.groups()[:4])
            end_h, end_m, end_s, end_ms = map(int, timestamp_match.groups()[4:])
            
            start_time = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000.0
            end_time = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000.0
            
            # Text is everything after the timestamp line
            text = '\n'.join(lines[2:]).strip()
            
            if text:
                segments.append(TextSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=1.0,
                    source="subtitle"
                ))
        
        # Sort by start_time to ensure monotonic order
        segments.sort(key=lambda s: s.start_time)
        return segments
    
    def _parse_json(self, subtitle_path: Path) -> List[TextSegment]:
        """Parse Bilibili JSON format subtitle file.

        Bilibili JSON format example:
        {
          "body": [
            {
              "from": 1.0,
              "to": 3.0,
              "content": "这是第一句字幕"
            }
          ]
        }

        Args:
            subtitle_path: Path to JSON file

        Returns:
            List of TextSegment objects
        """
        segments = []
        content = subtitle_path.read_text(encoding='utf-8')
        data = json.loads(content)
        
        # Extract body array
        body = data.get('body', [])
        
        for item in body:
            start_time = float(item.get('from', 0))
            end_time = float(item.get('to', 0))
            text = item.get('content', '').strip()
            
            if text:
                segments.append(TextSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=1.0,
                    source="subtitle"
                ))
        
        # Sort by start_time to ensure monotonic order
        segments.sort(key=lambda s: s.start_time)
        return segments
    
    def _parse_xml(self, subtitle_path: Path) -> List[TextSegment]:
        """Parse XML format subtitle file.

        XML format example:
        <subtitle>
          <body>
            <s from="1.0" to="3.0">这是第一句字幕</s>
          </body>
        </subtitle>

        Args:
            subtitle_path: Path to XML file

        Returns:
            List of TextSegment objects
        """
        segments = []
        tree = ET.parse(subtitle_path)
        root = tree.getroot()
        
        # Find all <s> elements (subtitle segments)
        # They can be directly under root or under a <body> element
        s_elements = root.findall('.//s')
        
        for s_elem in s_elements:
            start_time = float(s_elem.get('from', 0))
            end_time = float(s_elem.get('to', 0))
            text = (s_elem.text or '').strip()
            
            if text:
                segments.append(TextSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=1.0,
                    source="subtitle"
                ))
        
        # Sort by start_time to ensure monotonic order
        segments.sort(key=lambda s: s.start_time)
        return segments
