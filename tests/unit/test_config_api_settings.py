"""测试 Config 类的 API 配置项。

验证需求：7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
import logging
from pathlib import Path
from bilibili_extractor.core.config import Config, ConfigLoader


class TestConfigAPISettings:
    """测试 Config 类的 API 相关配置项。"""

    def test_config_default_values(self):
        """测试配置项的默认值。
        
        验证需求：7.1, 7.2, 7.3, 7.4
        """
        config = Config()

        # 验证默认值
        assert config.api_request_interval == 20  # 默认 20 秒
        assert config.api_retry_max_attempts == 3  # 默认 3 次
        assert config.api_retry_wait_time == 20  # 默认 20 秒

    def test_config_custom_values(self):
        """测试自定义配置值。"""
        config = Config(
            api_request_interval=30,
            api_retry_max_attempts=5,
            api_retry_wait_time=15,
        )

        # 验证自定义值
        assert config.api_request_interval == 30
        assert config.api_retry_max_attempts == 5
        assert config.api_retry_wait_time == 15

    def test_config_load_from_dict(self):
        """测试从字典加载配置。"""
        config_dict = {
            "api_request_interval": 25,
            "api_retry_max_attempts": 4,
            "api_retry_wait_time": 30,
        }

        config = Config(**config_dict)

        # 验证加载的值
        assert config.api_request_interval == 25
        assert config.api_retry_max_attempts == 4
        assert config.api_retry_wait_time == 30

    def test_config_validation_valid_values(self):
        """测试有效配置值的验证。
        
        验证需求：7.5
        """
        config = Config(
            api_request_interval=10,
            api_retry_max_attempts=5,
            api_retry_wait_time=15,
        )

        # 验证应该成功
        assert ConfigLoader.validate_config(config) is True

        # 值应该保持不变
        assert config.api_request_interval == 10
        assert config.api_retry_max_attempts == 5
        assert config.api_retry_wait_time == 15

    def test_config_validation_invalid_interval(self, caplog):
        """测试无效的 api_request_interval（非正整数）。
        
        验证需求：7.5
        """
        config = Config(api_request_interval=-5)

        # 验证应该成功，但会发出警告
        with caplog.at_level(logging.WARNING):
            assert ConfigLoader.validate_config(config) is True

        # 应该使用默认值
        assert config.api_request_interval == 20

        # 应该有警告日志
        assert "Invalid api_request_interval" in caplog.text
        assert "Using default: 20" in caplog.text

    def test_config_validation_invalid_max_attempts(self, caplog):
        """测试无效的 api_retry_max_attempts（非正整数）。
        
        验证需求：7.5
        """
        config = Config(api_retry_max_attempts=0)

        # 验证应该成功，但会发出警告
        with caplog.at_level(logging.WARNING):
            assert ConfigLoader.validate_config(config) is True

        # 应该使用默认值
        assert config.api_retry_max_attempts == 3

        # 应该有警告日志
        assert "Invalid api_retry_max_attempts" in caplog.text
        assert "Using default: 3" in caplog.text

    def test_config_validation_invalid_wait_time(self, caplog):
        """测试无效的 api_retry_wait_time（非正整数）。
        
        验证需求：7.5
        """
        config = Config(api_retry_wait_time=-10)

        # 验证应该成功，但会发出警告
        with caplog.at_level(logging.WARNING):
            assert ConfigLoader.validate_config(config) is True

        # 应该使用默认值
        assert config.api_retry_wait_time == 20

        # 应该有警告日志
        assert "Invalid api_retry_wait_time" in caplog.text
        assert "Using default: 20" in caplog.text

    def test_config_validation_zero_values(self, caplog):
        """测试所有配置项为 0 的情况。
        
        验证需求：7.5
        """
        config = Config(
            api_request_interval=0,
            api_retry_max_attempts=0,
            api_retry_wait_time=0,
        )

        # 验证应该成功，但会发出警告
        with caplog.at_level(logging.WARNING):
            assert ConfigLoader.validate_config(config) is True

        # 所有值应该恢复为默认值
        assert config.api_request_interval == 20
        assert config.api_retry_max_attempts == 3
        assert config.api_retry_wait_time == 20

        # 应该有 3 条警告日志
        assert caplog.text.count("Invalid") >= 3

    def test_config_validation_negative_values(self, caplog):
        """测试所有配置项为负数的情况。
        
        验证需求：7.5
        """
        config = Config(
            api_request_interval=-1,
            api_retry_max_attempts=-2,
            api_retry_wait_time=-3,
        )

        # 验证应该成功，但会发出警告
        with caplog.at_level(logging.WARNING):
            assert ConfigLoader.validate_config(config) is True

        # 所有值应该恢复为默认值
        assert config.api_request_interval == 20
        assert config.api_retry_max_attempts == 3
        assert config.api_retry_wait_time == 20

    def test_config_partial_custom_values(self):
        """测试部分自定义配置值。"""
        # 只自定义部分值，其他使用默认值
        config = Config(api_request_interval=15)

        # 验证自定义值
        assert config.api_request_interval == 15

        # 验证默认值
        assert config.api_retry_max_attempts == 3
        assert config.api_retry_wait_time == 20

    def test_config_extreme_values(self):
        """测试极端值。"""
        # 测试非常大的值
        config = Config(
            api_request_interval=3600,  # 1 小时
            api_retry_max_attempts=100,
            api_retry_wait_time=600,  # 10 分钟
        )

        # 验证应该成功（没有上限限制）
        assert ConfigLoader.validate_config(config) is True
        assert config.api_request_interval == 3600
        assert config.api_retry_max_attempts == 100
        assert config.api_retry_wait_time == 600

    def test_config_boundary_values(self):
        """测试边界值（最小有效值）。"""
        # 测试最小有效值（1）
        config = Config(
            api_request_interval=1,
            api_retry_max_attempts=1,
            api_retry_wait_time=1,
        )

        # 验证应该成功
        assert ConfigLoader.validate_config(config) is True
        assert config.api_request_interval == 1
        assert config.api_retry_max_attempts == 1
        assert config.api_retry_wait_time == 1
