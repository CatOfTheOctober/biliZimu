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
        
        # 禁用代理（解决代理连接问题）
        self.session.proxies = {
            'http': None,
            'https': None
        }
        
        # 配置请求头（完全复制 JS 版本的请求头）
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.bilibili.com',
            'Referer': 'https://www.bilibili.com/',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'X-Wbi-UA': 'Win32.Chrome.109.0.0.0',  # 关键：B站识别浏览器的标识
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

    def get_aid_from_bvid(self, bvid: str) -> int:
        """从 bvid 获取 aid（视频ID）。
        
        对应 JS 版本中的视频信息获取逻辑。
        
        Args:
            bvid: 视频的 BV 号
            
        Returns:
            aid: 视频的 AV 号
            
        Raises:
            BilibiliAPIError: 如果获取失败
        """
        from ..core.exceptions import BilibiliAPIError
        
        # 检查缓存
        cache_key = self._get_cache_key('aid_from_bvid', bvid)
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            self.logger.debug(f"使用缓存的 aid: {cached_value}")
            return cached_value
        
        # 速率限制
        self._rate_limiter.wait_if_needed()
        
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        
        try:
            self.logger.debug(f"获取 aid: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                error_msg = data.get('message', '未知错误')
                raise BilibiliAPIError(f"获取视频信息失败: {error_msg}")
            
            aid = data['data']['aid']
            
            # 缓存结果
            self._cache.set(cache_key, aid)
            
            self.logger.info(f"成功获取 aid: {aid}")
            return aid
            
        except Exception as e:
            self.logger.error(f"获取 aid 失败: {str(e)}")
            raise BilibiliAPIError(f"获取 aid 失败: {str(e)}")

    def _handle_wbi_request(self, url: str, **kwargs) -> Dict[str, Any]:
        """处理 WBI 请求的特殊逻辑。
        
        对应 JS 版本的 fetchWbiRequest 函数，包含：
        1. 详细的响应日志记录
        2. 字幕数据的特殊解析和记录
        3. 错误重试机制（添加 isGaiaAvoided=false 参数）
        4. 确保 Cookie 被正确发送
        
        Args:
            url: 请求 URL
            **kwargs: 其他请求参数
            
        Returns:
            dict: API 响应数据
        """
        import json
        from ..core.exceptions import BilibiliAPIError
        
        try:
            self.logger.info(f"检测到 WBI 接口请求，进行特殊处理: {url}")
            
            # 确保使用正确的请求头
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            
            # 合并默认请求头
            headers = self.session.headers.copy()
            headers.update(kwargs.get('headers', {}))
            kwargs['headers'] = headers
            
            # 确保超时设置
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout
            
            # 发起请求
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            data = response.json()
            
            # 详细日志记录
            self.logger.info("===== WBI接口响应数据开始 =====")
            self.logger.info(f"状态码: {data.get('code')}")
            self.logger.info(f"消息: {data.get('message')}")
            self.logger.debug(f"完整数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            # 字幕数据特殊处理
            if data.get('code') == 0 and data.get('data', {}).get('subtitle'):
                subtitle_data = data['data']['subtitle']
                subtitles = subtitle_data.get('subtitles', [])
                
                self.logger.info("===== 字幕数据详情 =====")
                self.logger.info(f"字幕列表数量: {len(subtitles)}")
                
                for i, sub in enumerate(subtitles):
                    self.logger.info(f"字幕[{i}]: id={sub.get('id')}, lan={sub.get('lan')}, "
                                  f"lan_doc={sub.get('lan_doc')}, url={sub.get('subtitle_url')}")
                
                if not subtitles:
                    self.logger.info("没有找到字幕数据")
                
                self.logger.info("===== 字幕数据详情结束 =====")
            
            # 错误重试机制
            if (data.get('code') == -400 and 
                data.get('message') and 
                'Key:' in data.get('message', '')):
                
                self.logger.warning(f"API返回参数错误，可能需要额外参数: {data.get('message')}")
                
                # 尝试添加 isGaiaAvoided=false 参数后再次请求
                if 'isGaiaAvoided=' not in url:
                    separator = '&' if '?' in url else '?'
                    retry_url = f"{url}{separator}isGaiaAvoided=false"
                    
                    self.logger.info(f"尝试添加参数后再次请求: {retry_url}")
                    
                    try:
                        retry_response = self.session.get(retry_url, **kwargs)
                        retry_response.raise_for_status()
                        retry_data = retry_response.json()
                        
                        self.logger.info("===== 参数补充后API响应 =====")
                        self.logger.info(f"状态码: {retry_data.get('code')}")
                        self.logger.info(f"消息: {retry_data.get('message')}")
                        self.logger.debug(f"完整数据: {json.dumps(retry_data, ensure_ascii=False, indent=2)}")
                        self.logger.info("===== 参数补充后API响应结束 =====")
                        
                        return retry_data
                        
                    except Exception as retry_error:
                        self.logger.error(f"参数补充后请求仍然失败: {str(retry_error)}")
                        # 返回原始错误
            
            self.logger.info("===== WBI接口响应数据结束 =====")
            return data
            
        except Exception as e:
            self.logger.error(f"WBI请求处理出错: {str(e)}")
            raise BilibiliAPIError(f"WBI请求处理出错: {str(e)}")

    def _make_request(self, url: str, **kwargs) -> Dict[str, Any]:
        """统一的请求处理函数。
        
        对应 JS 版本的 fetchWithHeaders 函数，包含：
        1. 检测 WBI 请求并进行特殊处理
        2. 统一的请求头管理
        3. 统一的错误处理
        
        Args:
            url: 请求 URL
            **kwargs: 其他请求参数
            
        Returns:
            dict: API 响应数据
        """
        from ..core.exceptions import BilibiliAPIError
        
        try:
            self.logger.debug(f"发起API请求: {url}")
            
            # 检查是否是 WBI 接口
            is_wbi_request = '/x/player/wbi/v2' in url
            
            if is_wbi_request:
                self.logger.info("检测到WBI接口请求，进行特殊处理")
                return self._handle_wbi_request(url, **kwargs)
            
            # 普通请求处理
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            
            # 合并默认请求头
            headers = self.session.headers.copy()
            headers.update(kwargs.get('headers', {}))
            kwargs['headers'] = headers
            
            # 确保超时设置
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout
            
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            data = response.json()
            
            self.logger.debug(f"API请求响应: code={data.get('code')}, message={data.get('message')}")
            return data
            
        except Exception as e:
            self.logger.error(f"API请求出错: {str(e)}")
            raise BilibiliAPIError(f"API请求出错: {str(e)}")

    @retry_on_error(max_retries=3, backoff_factor=0.5)
    def get_player_info(self, aid: int, cid: int) -> Dict[str, Any]:
        """获取播放器信息（包含字幕列表）。
        
        改进版本：
        1. 优先使用 aid+cid 调用 /x/player/wbi/v2（使用特殊处理）
        2. 如果失败，降级到 /x/player/v2
        3. 使用统一的请求处理函数
        
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
        
        # 检查缓存
        cache_key = self._get_cache_key('player_info', aid, cid)
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            self.logger.debug(f"使用缓存的播放器信息 aid={aid}, cid={cid}")
            return cached_value
        
        # 速率限制
        self._rate_limiter.wait_if_needed()
        
        # 方案1: 尝试 WBI API（使用特殊处理）
        try:
            self.logger.debug(f"尝试 WBI API aid={aid}, cid={cid}")
            
            # 使用 aid+cid 调用 WBI API（会触发特殊处理）
            url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
            
            # 使用统一请求函数（会自动检测 WBI 请求并特殊处理）
            data = self._make_request(url)
            
            # 检查 API 响应
            code = data.get('code')
            if code == -101:
                raise AuthenticationError("需要登录才能访问播放器信息")
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
                
                self.logger.info(f"WBI API 成功: 找到 {len(subtitles)} 个字幕")
                return result
            else:
                # WBI API 返回错误，尝试降级
                error_msg = data.get('message', '未知错误')
                self.logger.warning(f"WBI API 失败 (code: {code}, message: {error_msg}), 降级到 v2 API")
                
        except RiskControlError:
            # 重新抛出 RiskControlError
            raise
        except Exception as e:
            # WBI API 失败，记录日志并尝试降级
            self.logger.warning(f"WBI API 失败: {e}, 降级到 v2 API")
        
        # 方案2: 降级到 V2 API
        self.logger.debug(f"使用降级 v2 API aid={aid}, cid={cid}")
        url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
        
        try:
            self.logger.debug(f"从 v2 API 获取播放器信息")
            
            # 使用统一请求函数
            data = self._make_request(url)
            
            # 检查 API 响应
            code = data.get('code')
            if code == -101:
                raise AuthenticationError("需要登录才能访问播放器信息")
            elif code != 0:
                error_msg = data.get('message', '未知错误')
                raise BilibiliAPIError(f"API 错误: {error_msg} (code: {code})")
            
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
            
            self.logger.info(f"V2 API 成功: 找到 {len(subtitles)} 个字幕")
            return result
            
        except Exception as e:
            self.logger.error(f"获取播放器信息失败: {str(e)}")
            raise BilibiliAPIError(f"获取播放器信息失败: {str(e)}")

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
            self.logger.debug(f"获取AI字幕URL: {url}")
            
            # 使用统一请求函数
            data = self._make_request(url)
            
            # 检查API响应
            if data.get('code') != 0:
                error_msg = data.get('message', '未知错误')
                self.logger.warning(f"AI字幕API错误: {error_msg}")
                return None
            
            # 提取subtitle_url
            ai_data = data.get('data', {})
            subtitle_url = ai_data.get('subtitle_url')
            
            if subtitle_url:
                self.logger.debug(f"找到AI字幕URL: {subtitle_url}")
            else:
                self.logger.debug("该视频没有AI字幕")
            
            return subtitle_url
            
        except Exception as e:
            self.logger.error(f"获取AI字幕URL失败: {str(e)}")
            raise BilibiliAPIError(f"获取AI字幕URL失败: {str(e)}")

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
    def get_subtitle_with_ai_fallback(self, bvid: str, cid: int) -> Dict[str, Any]:
        """获取字幕，优先获取 AI 字幕（完全复制 JS 版本逻辑）。
        
        改进版本：
        1. 首先从 bvid 获取 aid
        2. 使用 aid+cid 获取播放器信息
        3. 优先选择 ai-zh 字幕
        4. 如果字幕 URL 为空，调用 AI 字幕 API 获取 URL
        5. 下载字幕内容
        
        Args:
            bvid: 视频 bvid
            cid: 视频 cid
            
        Returns:
            包含字幕数据的字典：
            {
                'success': bool,
                'metadata': {...},  # 字幕元数据
                'subtitles': [...],  # 字幕列表
                'subtitle_text': str,  # 格式化的字幕文本
            }
            
        Raises:
            BilibiliAPIError: API 调用失败
        """
        from ..core.exceptions import BilibiliAPIError
        
        try:
            self.logger.info(f"获取字幕，bvid={bvid}, cid={cid}")
            
            # 步骤1：从 bvid 获取 aid（对应 JS 版本逻辑）
            self.logger.debug("步骤1：从 bvid 获取 aid")
            try:
                aid = self.get_aid_from_bvid(bvid)
                self.logger.info(f"成功获取 aid: {aid}")
            except Exception as e:
                self.logger.warning(f"获取 aid 失败: {e}，将使用 bvid 方式")
                aid = None
            
            # 步骤2：获取播放器信息（包含字幕列表）
            self.logger.debug("步骤2：获取播放器信息")
            if aid:
                # 优先使用 aid+cid（对应 JS 版本逻辑）
                player_info = self.get_player_info(aid, cid)
            else:
                # 降级：如果没有 aid，尝试使用 bvid（虽然 JS 版本不这样做）
                self.logger.warning("没有 aid，尝试使用 bvid 获取播放器信息")
                # 这里我们需要一个备用方案，但 JS 版本总是有 aid
                # 为了兼容性，我们抛出错误
                raise BilibiliAPIError("无法获取 aid，无法继续获取字幕")
            
            subtitles = player_info.get('subtitles', [])
            
            if not subtitles:
                self.logger.warning("没有找到字幕列表")
                return {
                    'success': False,
                    'message': '该视频没有可用字幕',
                }
            
            self.logger.debug(f"找到 {len(subtitles)} 个字幕")
            
            # 步骤3：优先选择 ai-zh 字幕（完全复制 JS 逻辑）
            self.logger.debug("步骤3：优先选择 ai-zh 字幕")
            default_subtitle = None
            for subtitle in subtitles:
                if subtitle.get('lan') == 'ai-zh':
                    default_subtitle = subtitle
                    break
            
            if not default_subtitle:
                self.logger.warning("没有找到 ai-zh 字幕，尝试使用第一个字幕")
                default_subtitle = subtitles[0]
            
            self.logger.debug(f"选择字幕：{default_subtitle.get('lan')} - {default_subtitle.get('lan_doc')}")
            
            # 步骤4：获取字幕 URL
            subtitle_url = default_subtitle.get('subtitle_url')
            
            if not subtitle_url:
                self.logger.debug("字幕 URL 为空，检查是否是 AI 字幕")
                
                # 如果是 AI 字幕但 URL 为空，调用 AI 字幕 API
                if default_subtitle.get('lan', '').startswith('ai-'):
                    self.logger.debug("检测到 AI 字幕，调用 AI 字幕 API 获取 URL")
                    
                    # 调用 AI 字幕 API（需要 aid）
                    if aid:
                        ai_subtitle_url = self.get_ai_subtitle_url(aid, cid)
                        
                        if ai_subtitle_url:
                            subtitle_url = ai_subtitle_url
                            self.logger.debug(f"成功获取 AI 字幕 URL")
                        else:
                            self.logger.warning("无法获取 AI 字幕 URL")
                            return {
                                'success': False,
                                'message': '该视频有自动生成字幕，但无法获取字幕地址',
                            }
                    else:
                        self.logger.warning("没有 aid，无法调用 AI 字幕 API")
                        return {
                            'success': False,
                            'message': '无法获取 AI 字幕，缺少必要的视频信息',
                        }
                else:
                    self.logger.warning("字幕 URL 为空且不是 AI 字幕")
                    return {
                        'success': False,
                        'message': '字幕地址无效',
                    }
            
            # 步骤5：下载字幕内容
            self.logger.debug("步骤5：下载字幕内容")
            subtitle_data = self.download_subtitle(subtitle_url)
            
            # 检查字幕数据格式
            if not subtitle_data or not subtitle_data.get('body'):
                self.logger.warning("字幕内容为空或格式不正确")
                return {
                    'success': False,
                    'message': '解析字幕内容失败，可能是不支持的字幕格式',
                }
            
            # 步骤6：格式化字幕数据
            self.logger.debug("步骤6：格式化字幕数据")
            subtitle_body = subtitle_data.get('body', [])
            
            # 生成字幕元数据
            metadata = {
                'aid': aid,
                'bvid': bvid,
                'cid': cid,
                'lan': default_subtitle.get('lan'),
                'lan_doc': default_subtitle.get('lan_doc'),
                'subtitle_url': subtitle_url,
            }
            
            # 格式化字幕文本（SRT 和 TXT 格式）
            subtitle_text_srt = self._format_subtitles_to_srt(subtitle_body)
            subtitle_text_txt = self._format_subtitles_to_txt(subtitle_body)
            
            self.logger.info(f"成功获取字幕，共 {len(subtitle_body)} 条")
            
            return {
                'success': True,
                'metadata': metadata,
                'subtitles': subtitle_body,
                'subtitle_text_srt': subtitle_text_srt,  # SRT 格式字幕
                'subtitle_text_txt': subtitle_text_txt,  # TXT 格式字幕
                'subtitle_text': subtitle_text_txt,      # 默认使用 TXT 格式
            }
            
        except Exception as e:
            self.logger.error(f"获取字幕失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'获取字幕失败: {str(e)}',
            }
    
    def _format_subtitles_to_srt(self, subtitles: list) -> str:
        """将字幕列表格式化为 SRT 格式文本。
        
        Args:
            subtitles: 字幕列表，每个元素包含 from, to, content
            
        Returns:
            SRT 格式的字幕文本
        """
        srt_lines = []
        
        for index, subtitle in enumerate(subtitles, 1):
            start_time = self._format_time(subtitle.get('from', 0))
            end_time = self._format_time(subtitle.get('to', 0))
            content = subtitle.get('content', '')
            
            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(content)
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def _format_subtitles_to_txt(self, subtitles: list) -> str:
        """将字幕列表格式化为纯文本格式。
        
        Args:
            subtitles: 字幕列表，每个元素包含 from, to, content
            
        Returns:
            纯文本格式的字幕内容，每行一句话
        """
        txt_lines = []
        
        for subtitle in subtitles:
            content = subtitle.get('content', '').strip()
            if content:  # 只添加非空内容
                txt_lines.append(content)
        
        return "\n".join(txt_lines)
    
    def _format_time(self, seconds: float) -> str:
        """将秒数格式化为 HH:MM:SS,mmm 格式（SRT 格式）。
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

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
            
            self.logger.debug(f"下载字幕: {url}")
            
            # 使用统一请求函数
            data = self._make_request(url)
            
            self.logger.debug(f"字幕下载成功")
            return data
            
        except Exception as e:
            self.logger.error(f"字幕下载失败: {str(e)}")
            raise BilibiliAPIError(f"字幕下载失败: {str(e)}")
