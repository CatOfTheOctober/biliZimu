"""B站API客户端模块。"""

import logging
import time
import requests
from typing import Optional, Dict, Any, Callable, Tuple
from functools import wraps
from collections import OrderedDict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class RateLimiter:
    """简单的速率限制器。"""
    
    def __init__(self, min_interval: float = 20.0):
        """初始化速率限制器。
        
        Args:
            min_interval: 最小请求间隔（秒），默认 20 秒
        """
        self.min_interval = min_interval
        self.last_request_time = 0.0
    
    def wait_if_needed(self):
        """如果需要，等待以满足速率限制。"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()


def rate_limit(limiter: RateLimiter):
    """速率限制装饰器。
    
    Args:
        limiter: RateLimiter实例
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    return decorator


class LRUCache:
    """简单的LRU缓存实现（带TTL）。"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """初始化LRU缓存。
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒）
        """
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.timestamps: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期返回None
        """
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() - self.timestamps.get(key, 0) > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        # 移到末尾（最近使用）
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值。
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # 删除最旧的条目
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
        
        self.cache[key] = value
        self.timestamps[key] = time.time()


def retry_on_error(max_retries: int = 3, backoff_factor: float = 0.5):
    """API重试装饰器。
    
    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子（指数退避）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(__name__)
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.Timeout as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Request timeout, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Request failed after {max_retries} attempts")
                        raise
                except requests.HTTPError as e:
                    # 429限流响应，等待后重试
                    if e.response.status_code == 429:
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor * (2 ** attempt)
                            logger.warning(f"Rate limited (429), retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Rate limit exceeded after {max_retries} attempts")
                            raise
                    else:
                        raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Request failed: {e}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Request failed after {max_retries} attempts: {e}")
                        raise
            
        return wrapper
    return decorator


class BilibiliAPI:
    """B站API客户端。
    
    负责：
    1. 调用B站视频信息API
    2. 调用B站播放器信息API（获取字幕列表）
    3. 调用B站AI字幕API
    4. 下载字幕文件
    """
    
    def __init__(self, cookie: Optional[str] = None, config: Optional['Config'] = None):
        """初始化BilibiliAPI。
        
        Args:
            cookie: Cookie字符串（可选）
            config: 配置对象（可选）
        """
        self.cookie = cookie
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化HTTP会话
        self.session = requests.Session()
        
        # 配置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
        })
        
        # 如果有Cookie，添加到请求头
        if cookie:
            self.session.headers.update({
                'Cookie': cookie
            })
        
        # 配置连接池和超时
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 设置超时（连接5秒，读取30秒）
        self.timeout = (5, 30)
        
        # LRU缓存（最大100条，TTL 60秒）
        # 缩短TTL以减少缓存污染的风险
        self._cache = LRUCache(max_size=100, ttl=60)
        
        # 速率限制器（使用配置的请求间隔）
        request_interval = config.api_request_interval if config else 20
        self._rate_limiter = RateLimiter(min_interval=request_interval)
    
    def clear_cache(self) -> None:
        """清除所有缓存。
        
        用于避免缓存污染问题。
        """
        self._cache.cache.clear()
        self._cache.timestamps.clear()
        self.logger.debug("Cache cleared")
    
    def _get_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键。
        
        Args:
            prefix: 缓存键前缀
            *args: 缓存键参数
            
        Returns:
            缓存键字符串
        """
        return f"{prefix}:{'_'.join(str(arg) for arg in args)}"
    
    @retry_on_error(max_retries=3, backoff_factor=0.5)
    def get_video_info(self, bvid: str, page: int = 1) -> Dict[str, Any]:
        """获取视频信息。
        
        调用B站视频信息API获取aid、cid、title等信息。
        对于多P视频，根据page参数返回对应分P的cid。
        
        Args:
            bvid: 视频BVID
            page: 分P页码（从1开始），默认为1
            
        Returns:
            视频信息字典，包含aid、cid、title等字段
            
        Raises:
            BilibiliAPIError: API调用失败
        """
        from ..core.exceptions import BilibiliAPIError
        
        # 检查缓存（包含page参数）
        cache_key = self._get_cache_key('video_info', bvid, page)
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            self.logger.debug(f"Using cached video info for {bvid} page {page}")
            return cached_value
        
        # 速率限制
        self._rate_limiter.wait_if_needed()
        
        # 调用API
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        
        try:
            self.logger.debug(f"Fetching video info: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API响应
            if data.get('code') != 0:
                error_msg = data.get('message', 'Unknown error')
                raise BilibiliAPIError(f"API error: {error_msg} (code: {data.get('code')})")
            
            # 提取视频信息
            video_data = data.get('data', {})
            
            # 获取cid - 按照SubBatch的逻辑处理多P视频
            cid = video_data.get('cid')
            pages = video_data.get('pages', [])
            actual_page = page  # 实际使用的page（可能会调整）
            
            # 如果视频有多个分P，根据page参数获取对应的cid
            if pages and len(pages) > 0:
                # page是1-indexed，pages数组是0-indexed
                page_index = page - 1
                
                if 0 <= page_index < len(pages):
                    cid = pages[page_index].get('cid', cid)
                    self.logger.debug(f"Multi-page video: using page {page}, cid={cid}")
                else:
                    # 如果page超出范围，使用第一P
                    self.logger.warning(f"Page {page} out of range (total {len(pages)} pages), using page 1")
                    cid = pages[0].get('cid', cid)
                    actual_page = 1  # 调整实际使用的page
            elif not cid and pages and len(pages) > 0:
                # 如果cid为空但有pages数组，使用第一P的cid（SubBatch逻辑）
                cid = pages[0].get('cid')
                self.logger.debug(f"Using cid from pages[0]: {cid}")
            
            result = {
                'aid': video_data.get('aid'),
                'bvid': video_data.get('bvid'),
                'cid': cid,
                'title': video_data.get('title'),
                'pic': video_data.get('pic'),
                'duration': video_data.get('duration'),
                'pages': pages,  # 保留pages信息
                'page_count': len(pages) if pages else 1,
            }
            
            # 使用实际的page作为缓存键（避免缓存污染）
            actual_cache_key = self._get_cache_key('video_info', bvid, actual_page)
            self._cache.set(actual_cache_key, result)
            
            # 如果请求的page和实际page不同，也缓存到请求的page（避免重复请求）
            if actual_page != page:
                self._cache.set(cache_key, result)
            
            self.logger.debug(f"Video info retrieved: aid={result['aid']}, cid={result['cid']}, page={page}/{result['page_count']}")
            return result
            
        except requests.RequestException as e:
            raise BilibiliAPIError(f"Failed to fetch video info: {e}")

    @retry_on_error(max_retries=3, backoff_factor=0.5)
    def get_player_info(self, aid: int, cid: int) -> Dict[str, Any]:
        """获取播放器信息（包含字幕列表）。
        
        使用 WBI 签名请求 WBI API，如果失败则降级到 V2 API。
        
        Args:
            aid: 视频 aid
            cid: 视频 cid
            
        Returns:
            播放器信息字典，包含字幕列表
            
        Raises:
            RiskControlError: 触发风控（HTTP 412）
            BilibiliAPIError: API 调用失败
            AuthenticationError: 需要登录
        """
        from ..core.exceptions import BilibiliAPIError, AuthenticationError, RiskControlError
        from .wbi_sign import get_wbi_keys, encode_wbi
        
        # 检查缓存
        cache_key = self._get_cache_key('player_info', aid, cid)
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            self.logger.debug(f"Using cached player info for aid={aid}, cid={cid}")
            return cached_value
        
        # 速率限制
        self._rate_limiter.wait_if_needed()
        
        # 方案1: 尝试 WBI API（优先）
        try:
            self.logger.debug(f"Trying WBI API for aid={aid}, cid={cid}")
            
            # 获取 WBI 密钥
            wbi_keys = get_wbi_keys()
            if wbi_keys:
                img_key, sub_key = wbi_keys
                
                # 构建参数并进行 WBI 签名
                params = {'aid': aid, 'cid': cid}
                signed_params = encode_wbi(params, img_key, sub_key)
                
                # 构建 URL
                query_string = '&'.join(f"{k}={v}" for k, v in signed_params.items())
                url = f"https://api.bilibili.com/x/player/wbi/v2?{query_string}"
                
                self.logger.debug(f"Fetching WBI API with signature: {url[:100]}...")
                response = self.session.get(url, timeout=self.timeout)
            else:
                # 无法获取 WBI 密钥，尝试不带签名的请求
                url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
                self.logger.debug(f"Fetching WBI API without signature: {url}")
                response = self.session.get(url, timeout=self.timeout)
            
            # 检测 412 风控错误
            if response.status_code == 412:
                self.logger.warning(
                    f"Risk control triggered (412) for aid={aid}, cid={cid}"
                )
                raise RiskControlError(
                    message=f"Risk control triggered (HTTP 412) for aid={aid}, cid={cid}",
                    video_id=f"aid={aid},cid={cid}",
                    suggested_wait_time=20,
                    request_url=url
                )
            
            response.raise_for_status()
            
            data = response.json()
            
            # 检查 API 响应
            code = data.get('code')
            if code == -101:
                raise AuthenticationError("Login required to access player info")
            elif code == 0:
                # WBI API 成功
                player_data = data.get('data', {})
                subtitle_data = player_data.get('subtitle', {})
                subtitles = subtitle_data.get('subtitles', [])
                
                result = {
                    'subtitles': subtitles,
                    'subtitle_data': subtitle_data,
                }
                
                # 缓存结果
                self._cache.set(cache_key, result)
                
                self.logger.info(f"WBI API succeeded: {len(subtitles)} subtitles found")
                return result
            else:
                # WBI API 返回错误，尝试降级
                error_msg = data.get('message', 'Unknown error')
                self.logger.warning(f"WBI API failed (code: {code}, message: {error_msg}), falling back to v2 API")
                
        except RiskControlError:
            # 重新抛出 RiskControlError
            raise
        except Exception as e:
            # WBI API 失败，记录日志并尝试降级
            self.logger.warning(f"WBI API failed: {e}, falling back to v2 API")
        
        # 方案2: 降级到 V2 API
        self.logger.debug(f"Using fallback v2 API for aid={aid}, cid={cid}")
        url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
        
        try:
            self.logger.debug(f"Fetching player info from v2 API")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查 API 响应
            code = data.get('code')
            if code == -101:
                raise AuthenticationError("Login required to access player info")
            elif code != 0:
                error_msg = data.get('message', 'Unknown error')
                raise BilibiliAPIError(f"API error: {error_msg} (code: {code})")
            
            # 提取播放器信息
            player_data = data.get('data', {})
            subtitle_data = player_data.get('subtitle', {})
            subtitles = subtitle_data.get('subtitles', [])
            
            result = {
                'subtitles': subtitles,
                'subtitle_data': subtitle_data,
            }
            
            # 缓存结果
            self._cache.set(cache_key, result)
            
            self.logger.info(f"V2 API succeeded: {len(subtitles)} subtitles found")
            return result
            
        except requests.RequestException as e:
            raise BilibiliAPIError(f"Failed to fetch player info: {e}")

    @retry_on_error(max_retries=3, backoff_factor=0.5)
    def get_ai_subtitle_url(self, aid: int, cid: int) -> Optional[str]:
        """获取AI字幕URL。
        
        当播放器API返回的字幕URL为空时，调用此API获取AI字幕URL。
        需要Cookie才能访问。
        
        Args:
            aid: 视频aid
            cid: 视频cid
            
        Returns:
            AI字幕URL，如果不可用返回None
            
        Raises:
            BilibiliAPIError: API调用失败
        """
        from ..core.exceptions import BilibiliAPIError
        
        # 速率限制
        self._rate_limiter.wait_if_needed()
        
        # 调用API
        url = f"https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}"
        
        try:
            self.logger.debug(f"Fetching AI subtitle URL: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API响应
            if data.get('code') != 0:
                error_msg = data.get('message', 'Unknown error')
                self.logger.warning(f"AI subtitle API error: {error_msg}")
                return None
            
            # 提取subtitle_url
            ai_data = data.get('data', {})
            subtitle_url = ai_data.get('subtitle_url')
            
            if subtitle_url:
                self.logger.debug(f"AI subtitle URL found: {subtitle_url}")
            else:
                self.logger.debug("AI subtitle not available for this video")
            
            return subtitle_url
            
        except requests.RequestException as e:
            raise BilibiliAPIError(f"Failed to fetch AI subtitle URL: {e}")

    def format_subtitle_url(self, url: str) -> str:
        """格式化字幕URL。
        
        处理相对路径：
        - 如果URL以//开头，添加https:前缀
        - 如果URL以/开头，添加https://api.bilibili.com前缀
        
        Args:
            url: 原始URL
            
        Returns:
            格式化后的完整URL
        """
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return 'https://api.bilibili.com' + url
        else:
            return url
    
    @retry_on_error(max_retries=3, backoff_factor=0.5)
    def download_subtitle(self, subtitle_url: str) -> Dict[str, Any]:
        """下载字幕文件。
        
        Args:
            subtitle_url: 字幕URL
            
        Returns:
            字幕JSON数据
            
        Raises:
            BilibiliAPIError: 下载失败
        """
        from ..core.exceptions import BilibiliAPIError
        
        try:
            # 格式化URL
            url = self.format_subtitle_url(subtitle_url)
            
            # 速率限制
            self._rate_limiter.wait_if_needed()
            
            self.logger.debug(f"Downloading subtitle: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Subtitle downloaded successfully")
            
            return data
            
        except requests.RequestException as e:
            raise BilibiliAPIError(f"Failed to download subtitle: {e}")
        except ValueError as e:
            raise BilibiliAPIError(f"Invalid subtitle JSON: {e}")
