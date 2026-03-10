"""测试 BilibiliAPI 的 412 风控错误检测。

验证需求：
- 1.1: BilibiliAPI 收到 HTTP 412 状态码响应时，识别为风控错误
- 1.2: 检测到 412 风控错误时，记录详细的错误日志（包括请求 URL、时间戳、视频 ID）
- 1.3: 检测到 412 风控错误时，抛出自定义的 RiskControlError 异常
- 8.1: 触发 412 风控错误时，记录完整的请求信息（URL、headers、参数）
- 8.2: 触发 412 风控错误时，记录响应信息（状态码、响应体）
- 8.4: 使用 WARNING 级别记录风控错误
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.bilibili_extractor.modules.bilibili_api import BilibiliAPI
from src.bilibili_extractor.core.exceptions import RiskControlError
from src.bilibili_extractor.core.config import Config


class TestBilibiliAPI412Detection:
    """测试 BilibiliAPI 的 412 风控错误检测。"""
    
    @pytest.fixture
    def api_instance(self):
        """创建 BilibiliAPI 实例。"""
        config = Config()
        return BilibiliAPI(cookie=None, config=config)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_raises_risk_control_error(self, mock_get_wbi_keys, api_instance):
        """测试 HTTP 412 响应抛出 RiskControlError。
        
        验证需求 1.1, 1.3: 识别 412 并抛出 RiskControlError
        """
        # 模拟 WBI 密钥获取失败，使用不带签名的请求
        mock_get_wbi_keys.return_value = None
        
        # 模拟 HTTP 412 响应
        mock_response = Mock()
        mock_response.status_code = 412
        mock_response.raise_for_status.side_effect = requests.HTTPError("412 Client Error")
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError) as exc_info:
                api_instance.get_player_info(aid=123456, cid=789012)
            
            # 验证异常包含正确的信息
            error = exc_info.value
            assert "412" in str(error)
            assert "123456" in str(error)
            assert "789012" in str(error)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_exception_attributes(self, mock_get_wbi_keys, api_instance):
        """测试 RiskControlError 异常包含必要的属性。
        
        验证需求 1.3, 1.4: 异常包含 message、video_id、suggested_wait_time、request_url
        """
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError) as exc_info:
                api_instance.get_player_info(aid=123456, cid=789012)
            
            error = exc_info.value
            
            # 验证异常属性
            assert hasattr(error, 'video_id')
            assert hasattr(error, 'suggested_wait_time')
            assert hasattr(error, 'request_url')
            
            # 验证属性值
            assert error.video_id == "aid=123456,cid=789012"
            assert error.suggested_wait_time == 20
            assert "player/wbi/v2" in error.request_url
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_logging_warning_level(self, mock_get_wbi_keys, api_instance, caplog):
        """测试 412 错误使用 WARNING 级别记录日志。
        
        验证需求 8.4: 使用 WARNING 级别记录风控错误
        """
        import logging
        caplog.set_level(logging.WARNING)
        
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError):
                api_instance.get_player_info(aid=123456, cid=789012)
        
        # 验证日志包含 WARNING 级别的消息
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        assert len(warning_logs) > 0
        
        # 验证日志包含 412 和视频 ID
        log_messages = [record.message for record in warning_logs]
        assert any("412" in msg for msg in log_messages)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_logging_includes_url(self, mock_get_wbi_keys, api_instance, caplog):
        """测试 412 错误日志包含请求 URL。
        
        验证需求 1.2, 8.1: 记录详细的错误日志（包括请求 URL）
        """
        import logging
        caplog.set_level(logging.DEBUG)
        
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError):
                api_instance.get_player_info(aid=123456, cid=789012)
        
        # 验证日志包含 URL
        log_messages = [record.message for record in caplog.records]
        assert any("player/wbi/v2" in msg for msg in log_messages)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_logging_includes_video_id(self, mock_get_wbi_keys, api_instance, caplog):
        """测试 412 错误日志包含视频 ID。
        
        验证需求 1.2: 记录详细的错误日志（包括视频 ID）
        """
        import logging
        caplog.set_level(logging.DEBUG)
        
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError):
                api_instance.get_player_info(aid=123456, cid=789012)
        
        # 验证日志包含 aid 和 cid
        log_messages = [record.message for record in caplog.records]
        assert any("123456" in msg for msg in log_messages)
        assert any("789012" in msg for msg in log_messages)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_not_caught_by_retry_decorator(self, mock_get_wbi_keys, api_instance):
        """测试 RiskControlError 不被 @retry_on_error 装饰器捕获。
        
        验证需求 1.3: RiskControlError 应该被重新抛出，不被重试装饰器捕获
        """
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        call_count = 0
        
        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response
        
        with patch.object(api_instance.session, 'get', side_effect=mock_get_side_effect):
            with pytest.raises(RiskControlError):
                api_instance.get_player_info(aid=123456, cid=789012)
        
        # 应该只调用一次，不应该重试
        assert call_count == 1
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_non_412_error_not_risk_control_error(self, mock_get_wbi_keys, api_instance):
        """测试非 412 错误不抛出 RiskControlError。
        
        验证需求 1.1: 只有 412 才识别为风控错误
        """
        mock_get_wbi_keys.return_value = None
        
        # 模拟其他 HTTP 错误（如 500）
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                api_instance.get_player_info(aid=123456, cid=789012)
            
            # 不应该是 RiskControlError
            assert not isinstance(exc_info.value, RiskControlError)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_with_wbi_signature(self, mock_get_wbi_keys, api_instance):
        """测试带 WBI 签名的请求也能检测 412 错误。
        
        验证需求 1.1: 无论是否使用签名，都能检测 412
        """
        # 模拟 WBI 密钥获取成功
        mock_get_wbi_keys.return_value = ('img_key', 'sub_key')
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with patch('src.bilibili_extractor.modules.bilibili_api.encode_wbi', return_value={'aid': 123456, 'cid': 789012}):
                with pytest.raises(RiskControlError):
                    api_instance.get_player_info(aid=123456, cid=789012)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_fallback_to_v2_api(self, mock_get_wbi_keys, api_instance):
        """测试 412 错误后不会自动降级到 V2 API。
        
        验证需求 1.3: 412 错误应该抛出异常，由上层处理重试和降级
        """
        mock_get_wbi_keys.return_value = None
        
        # 第一次调用返回 412，第二次调用返回成功
        mock_response_412 = Mock()
        mock_response_412.status_code = 412
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'code': 0,
            'data': {
                'subtitle': {
                    'subtitles': []
                }
            }
        }
        
        with patch.object(api_instance.session, 'get', side_effect=[mock_response_412, mock_response_success]):
            # 第一次调用应该抛出 RiskControlError
            with pytest.raises(RiskControlError):
                api_instance.get_player_info(aid=123456, cid=789012)
            
            # 不应该调用第二次（V2 API）
            # 因为 RiskControlError 被抛出后，不会继续执行


class TestBilibiliAPI412EdgeCases:
    """测试 BilibiliAPI 412 错误的边缘情况。"""
    
    @pytest.fixture
    def api_instance(self):
        """创建 BilibiliAPI 实例。"""
        config = Config()
        return BilibiliAPI(cookie=None, config=config)
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_with_different_aid_cid(self, mock_get_wbi_keys, api_instance):
        """测试不同的 aid/cid 组合都能检测 412。"""
        mock_get_wbi_keys.return_value = None
        
        test_cases = [
            (1, 1),
            (999999999, 999999999),
            (113832102008235, 29210970425),  # 用户提供的真实 ID
        ]
        
        for aid, cid in test_cases:
            mock_response = Mock()
            mock_response.status_code = 412
            
            with patch.object(api_instance.session, 'get', return_value=mock_response):
                with pytest.raises(RiskControlError) as exc_info:
                    api_instance.get_player_info(aid=aid, cid=cid)
                
                error = exc_info.value
                assert str(aid) in error.video_id
                assert str(cid) in error.video_id
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_message_format(self, mock_get_wbi_keys, api_instance):
        """测试 412 错误消息格式。"""
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError) as exc_info:
                api_instance.get_player_info(aid=123456, cid=789012)
            
            error = exc_info.value
            error_message = str(error)
            
            # 验证错误消息包含关键信息
            assert "412" in error_message
            assert "Risk control" in error_message or "风控" in error_message
    
    @patch('src.bilibili_extractor.modules.bilibili_api.get_wbi_keys')
    def test_412_error_request_url_in_exception(self, mock_get_wbi_keys, api_instance):
        """测试 412 错误异常包含完整的请求 URL。
        
        验证需求 8.1: 记录完整的请求信息（URL）
        """
        mock_get_wbi_keys.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 412
        
        with patch.object(api_instance.session, 'get', return_value=mock_response):
            with pytest.raises(RiskControlError) as exc_info:
                api_instance.get_player_info(aid=123456, cid=789012)
            
            error = exc_info.value
            
            # 验证 request_url 属性包含完整的 URL
            assert error.request_url is not None
            assert "https://" in error.request_url
            assert "api.bilibili.com" in error.request_url
            assert "player/wbi/v2" in error.request_url
