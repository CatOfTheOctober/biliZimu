"""测试 RateLimiter 的间隔控制功能。

验证需求：
- 5.1: RateLimiter 确保两次 API 请求之间至少间隔 20 秒
- 5.2: BilibiliAPI 准备发送请求时，RateLimiter 检查距离上次请求的时间间隔
- 5.3: 如果时间间隔小于 20 秒，RateLimiter 等待直到满足 20 秒间隔
- 5.4: RateLimiter 记录每次请求的时间戳
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from src.bilibili_extractor.modules.bilibili_api import RateLimiter


class TestRateLimiterDefaultInterval:
    """测试 RateLimiter 的默认间隔。"""
    
    def test_default_interval_is_20_seconds(self):
        """测试默认间隔为 20 秒。
        
        验证需求 5.1: RateLimiter 确保两次 API 请求之间至少间隔 20 秒
        """
        rate_limiter = RateLimiter()
        assert rate_limiter.min_interval == 20.0
    
    def test_initial_last_request_time_is_zero(self):
        """测试初始时间戳为 0。
        
        验证需求 5.4: RateLimiter 记录每次请求的时间戳
        """
        rate_limiter = RateLimiter()
        assert rate_limiter.last_request_time == 0.0


class TestRateLimiterCustomInterval:
    """测试 RateLimiter 的自定义间隔。"""
    
    def test_custom_interval_10_seconds(self):
        """测试自定义间隔为 10 秒。"""
        rate_limiter = RateLimiter(min_interval=10.0)
        assert rate_limiter.min_interval == 10.0
    
    def test_custom_interval_30_seconds(self):
        """测试自定义间隔为 30 秒。"""
        rate_limiter = RateLimiter(min_interval=30.0)
        assert rate_limiter.min_interval == 30.0
    
    def test_custom_interval_1_second(self):
        """测试自定义间隔为 1 秒。"""
        rate_limiter = RateLimiter(min_interval=1.0)
        assert rate_limiter.min_interval == 1.0


class TestRateLimiterWaitLogic:
    """测试 RateLimiter 的等待逻辑。"""
    
    @patch('time.time')
    @patch('time.sleep')
    def test_first_request_no_wait(self, mock_sleep, mock_time):
        """测试第一次请求不需要等待。
        
        验证需求 5.2: BilibiliAPI 准备发送请求时，RateLimiter 检查距离上次请求的时间间隔
        """
        # 模拟时间
        mock_time.return_value = 100.0
        
        rate_limiter = RateLimiter(min_interval=20.0)
        rate_limiter.wait_if_needed()
        
        # 第一次请求不应该等待
        mock_sleep.assert_not_called()
        # 应该记录时间戳
        assert rate_limiter.last_request_time == 100.0
    
    @patch('time.time')
    @patch('time.sleep')
    def test_second_request_within_interval_waits(self, mock_sleep, mock_time):
        """测试间隔不足时需要等待。
        
        验证需求 5.3: 如果时间间隔小于 20 秒，RateLimiter 等待直到满足 20 秒间隔
        """
        # 模拟时间序列
        time_sequence = [100.0, 110.0, 110.0]  # 第一次请求，第二次请求（间隔10秒），等待后
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=20.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        assert rate_limiter.last_request_time == 100.0
        
        # 第二次请求（间隔 10 秒，不足 20 秒）
        rate_limiter.wait_if_needed()
        
        # 应该等待 10 秒（20 - 10）
        mock_sleep.assert_called_once_with(10.0)
        # 应该更新时间戳
        assert rate_limiter.last_request_time == 110.0
    
    @patch('time.time')
    @patch('time.sleep')
    def test_second_request_after_interval_no_wait(self, mock_sleep, mock_time):
        """测试间隔充足时不需要等待。
        
        验证需求 5.2: BilibiliAPI 准备发送请求时，RateLimiter 检查距离上次请求的时间间隔
        """
        # 模拟时间序列
        time_sequence = [100.0, 125.0]  # 第一次请求，第二次请求（间隔25秒）
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=20.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        assert rate_limiter.last_request_time == 100.0
        
        # 第二次请求（间隔 25 秒，超过 20 秒）
        rate_limiter.wait_if_needed()
        
        # 不应该等待
        mock_sleep.assert_not_called()
        # 应该更新时间戳
        assert rate_limiter.last_request_time == 125.0
    
    @patch('time.time')
    @patch('time.sleep')
    def test_exact_interval_no_wait(self, mock_sleep, mock_time):
        """测试刚好满足间隔时不需要等待。
        
        验证需求 5.2: BilibiliAPI 准备发送请求时，RateLimiter 检查距离上次请求的时间间隔
        """
        # 模拟时间序列
        time_sequence = [100.0, 120.0]  # 第一次请求，第二次请求（间隔20秒）
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=20.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        
        # 第二次请求（间隔刚好 20 秒）
        rate_limiter.wait_if_needed()
        
        # 不应该等待
        mock_sleep.assert_not_called()
        # 应该更新时间戳
        assert rate_limiter.last_request_time == 120.0


class TestRateLimiterTimestampRecording:
    """测试 RateLimiter 的时间戳记录。"""
    
    @patch('time.time')
    @patch('time.sleep')
    def test_timestamp_updated_after_each_request(self, mock_sleep, mock_time):
        """测试每次请求后都更新时间戳。
        
        验证需求 5.4: RateLimiter 记录每次请求的时间戳
        """
        # 模拟时间序列
        time_sequence = [100.0, 125.0, 150.0]
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=20.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        assert rate_limiter.last_request_time == 100.0
        
        # 第二次请求
        rate_limiter.wait_if_needed()
        assert rate_limiter.last_request_time == 125.0
        
        # 第三次请求
        rate_limiter.wait_if_needed()
        assert rate_limiter.last_request_time == 150.0
    
    @patch('time.time')
    @patch('time.sleep')
    def test_timestamp_updated_even_with_wait(self, mock_sleep, mock_time):
        """测试即使需要等待，时间戳也会更新。
        
        验证需求 5.4: RateLimiter 记录每次请求的时间戳
        """
        # 模拟时间序列
        time_sequence = [100.0, 110.0, 110.0]  # 第一次，第二次（需要等待），等待后
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=20.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        assert rate_limiter.last_request_time == 100.0
        
        # 第二次请求（需要等待）
        rate_limiter.wait_if_needed()
        
        # 时间戳应该更新为等待后的时间
        assert rate_limiter.last_request_time == 110.0


class TestRateLimiterMultipleRequests:
    """测试 RateLimiter 处理多个连续请求。"""
    
    @patch('time.time')
    @patch('time.sleep')
    def test_three_consecutive_requests_with_short_intervals(self, mock_sleep, mock_time):
        """测试三个连续的短间隔请求。
        
        验证需求 5.1, 5.3: 确保间隔并在不足时等待
        """
        # 模拟时间序列
        time_sequence = [
            100.0,  # 第一次请求
            105.0, 105.0,  # 第二次请求（间隔5秒，需要等待15秒）
            110.0, 110.0,  # 第三次请求（间隔5秒，需要等待15秒）
        ]
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=20.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        assert mock_sleep.call_count == 0
        
        # 第二次请求（需要等待 15 秒）
        rate_limiter.wait_if_needed()
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(15.0)
        
        # 第三次请求（需要等待 15 秒）
        rate_limiter.wait_if_needed()
        assert mock_sleep.call_count == 2
        # 检查最后一次调用
        assert mock_sleep.call_args_list[-1][0][0] == 15.0
    
    @patch('time.time')
    @patch('time.sleep')
    def test_custom_interval_with_multiple_requests(self, mock_sleep, mock_time):
        """测试自定义间隔的多个请求。"""
        # 模拟时间序列
        time_sequence = [
            100.0,  # 第一次请求
            105.0, 105.0,  # 第二次请求（间隔5秒，需要等待5秒以满足10秒间隔）
        ]
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=10.0)
        
        # 第一次请求
        rate_limiter.wait_if_needed()
        
        # 第二次请求（需要等待 5 秒）
        rate_limiter.wait_if_needed()
        
        mock_sleep.assert_called_once_with(5.0)


class TestRateLimiterEdgeCases:
    """测试 RateLimiter 的边缘情况。"""
    
    @patch('time.time')
    @patch('time.sleep')
    def test_very_small_interval(self, mock_sleep, mock_time):
        """测试非常小的间隔（0.1秒）。"""
        time_sequence = [100.0, 100.05, 100.05]
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=0.1)
        
        rate_limiter.wait_if_needed()
        rate_limiter.wait_if_needed()
        
        # 应该等待 0.05 秒
        mock_sleep.assert_called_once_with(0.05)
    
    @patch('time.time')
    @patch('time.sleep')
    def test_zero_interval(self, mock_sleep, mock_time):
        """测试零间隔（不限制）。"""
        time_sequence = [100.0, 100.0]
        mock_time.side_effect = time_sequence
        
        rate_limiter = RateLimiter(min_interval=0.0)
        
        rate_limiter.wait_if_needed()
        rate_limiter.wait_if_needed()
        
        # 不应该等待
        mock_sleep.assert_not_called()
