"""异常类定义。"""


class BilibiliExtractorError(Exception):
    """基础异常类。"""
    pass


# 认证相关异常
class AuthenticationError(BilibiliExtractorError):
    """认证失败异常。"""
    pass


class CookieNotFoundError(AuthenticationError):
    """Cookie文件未找到异常。"""
    pass


class CookieInvalidError(AuthenticationError):
    """Cookie格式无效异常。"""
    pass


# API相关异常
class BilibiliAPIError(BilibiliExtractorError):
    """B站API调用失败异常。"""
    pass


class VideoNotFoundError(BilibiliAPIError):
    """视频不存在异常。"""
    pass


class SubtitleNotFoundError(BilibiliExtractorError):
    """字幕不存在异常。"""
    pass


# 风控相关异常
class RiskControlError(BilibiliAPIError):
    """B站 API 风控错误（HTTP 412）。
    
    Attributes:
        message: 错误消息
        video_id: 视频 ID（aid 或 bvid）
        suggested_wait_time: 建议等待时间（秒）
        request_url: 触发风控的请求 URL
    """
    
    def __init__(
        self,
        message: str,
        video_id: str = "",
        suggested_wait_time: int = 20,
        request_url: str = ""
    ):
        """初始化风控错误。
        
        Args:
            message: 错误消息
            video_id: 视频 ID
            suggested_wait_time: 建议等待时间（默认 20 秒）
            request_url: 请求 URL
        """
        super().__init__(message)
        self.video_id = video_id
        self.suggested_wait_time = suggested_wait_time
        self.request_url = request_url


# 字幕验证相关异常
class SubtitleValidationError(BilibiliExtractorError):
    """字幕验证失败异常。"""
    pass


class SubtitleMismatchError(SubtitleValidationError):
    """字幕与视频不匹配错误。
    
    Attributes:
        message: 错误消息
        requested_aid: 请求的 aid
        requested_cid: 请求的 cid
        returned_aid: 返回的 aid
        returned_cid: 返回的 cid
    """
    
    def __init__(
        self,
        message: str,
        requested_aid: int = 0,
        requested_cid: int = 0,
        returned_aid: int = 0,
        returned_cid: int = 0
    ):
        """初始化字幕不匹配错误。
        
        Args:
            message: 错误消息
            requested_aid: 请求的 aid
            requested_cid: 请求的 cid
            returned_aid: 返回的 aid
            returned_cid: 返回的 cid
        """
        super().__init__(message)
        self.requested_aid = requested_aid
        self.requested_cid = requested_cid
        self.returned_aid = returned_aid
        self.returned_cid = returned_cid

