"""测试 RiskControlError 异常类。

验证需求：1.3, 1.4
"""

import pytest
from bilibili_extractor.core.exceptions import RiskControlError, BilibiliAPIError


class TestRiskControlError:
    """测试 RiskControlError 异常类。"""
    
    def test_risk_control_error_creation(self):
        """测试创建 RiskControlError 异常。"""
        # 创建异常
        error = RiskControlError(
            message="Test error",
            video_id="BV1234567890",
            suggested_wait_time=30,
            request_url="https://api.bilibili.com/test"
        )
        
        # 验证属性
        assert str(error) == "Test error"
        assert error.video_id == "BV1234567890"
        assert error.suggested_wait_time == 30
        assert error.request_url == "https://api.bilibili.com/test"
    
    def test_risk_control_error_default_values(self):
        """测试 RiskControlError 的默认值。"""
        # 只传递必需的 message 参数
        error = RiskControlError("Test error")
        
        # 验证默认值
        assert str(error) == "Test error"
        assert error.video_id == ""
        assert error.suggested_wait_time == 20  # 默认 20 秒
        assert error.request_url == ""
    
    def test_risk_control_error_inheritance(self):
        """测试 RiskControlError 继承自 BilibiliAPIError。"""
        error = RiskControlError("Test error")
        
        # 验证继承关系
        assert isinstance(error, RiskControlError)
        assert isinstance(error, BilibiliAPIError)
        assert isinstance(error, Exception)
    
    def test_risk_control_error_message_format(self):
        """测试 RiskControlError 的错误消息格式。"""
        # 创建带有详细信息的异常
        error = RiskControlError(
            message="Risk control triggered (HTTP 412) for aid=123456, cid=789012",
            video_id="aid=123456,cid=789012",
            suggested_wait_time=20,
            request_url="https://api.bilibili.com/x/player/wbi/v2?aid=123456&cid=789012"
        )
        
        # 验证消息格式
        assert "Risk control triggered" in str(error)
        assert "HTTP 412" in str(error)
        assert "aid=123456" in str(error)
        assert "cid=789012" in str(error)
        
        # 验证属性
        assert error.video_id == "aid=123456,cid=789012"
        assert error.suggested_wait_time == 20
        assert "wbi/v2" in error.request_url
    
    def test_risk_control_error_can_be_raised(self):
        """测试 RiskControlError 可以被抛出和捕获。"""
        with pytest.raises(RiskControlError) as exc_info:
            raise RiskControlError(
                message="Test error",
                video_id="BV1234567890",
                suggested_wait_time=20,
                request_url="https://api.bilibili.com/test"
            )
        
        # 验证捕获的异常
        error = exc_info.value
        assert str(error) == "Test error"
        assert error.video_id == "BV1234567890"
        assert error.suggested_wait_time == 20
        assert error.request_url == "https://api.bilibili.com/test"
    
    def test_risk_control_error_can_be_caught_as_bilibili_api_error(self):
        """测试 RiskControlError 可以作为 BilibiliAPIError 被捕获。"""
        with pytest.raises(BilibiliAPIError):
            raise RiskControlError("Test error")
    
    def test_risk_control_error_with_different_wait_times(self):
        """测试不同的建议等待时间。"""
        # 测试不同的等待时间
        for wait_time in [10, 20, 30, 60]:
            error = RiskControlError(
                message="Test error",
                suggested_wait_time=wait_time
            )
            assert error.suggested_wait_time == wait_time
