"""测试 SubtitleMismatchError 异常类。

验证需求：9.3
"""

import pytest
from bilibili_extractor.core.exceptions import (
    SubtitleMismatchError,
    SubtitleValidationError,
)


class TestSubtitleMismatchError:
    """测试 SubtitleMismatchError 异常类。"""

    def test_subtitle_mismatch_error_creation(self):
        """测试创建 SubtitleMismatchError 异常。"""
        # 创建异常
        error = SubtitleMismatchError(
            message="Subtitle mismatch",
            requested_aid=123456,
            requested_cid=789012,
            returned_aid=111111,
            returned_cid=222222,
        )

        # 验证属性
        assert str(error) == "Subtitle mismatch"
        assert error.requested_aid == 123456
        assert error.requested_cid == 789012
        assert error.returned_aid == 111111
        assert error.returned_cid == 222222

    def test_subtitle_mismatch_error_default_values(self):
        """测试 SubtitleMismatchError 的默认值。"""
        # 只传递必需的 message 参数
        error = SubtitleMismatchError("Test error")

        # 验证默认值（所有 id 为 0）
        assert str(error) == "Test error"
        assert error.requested_aid == 0
        assert error.requested_cid == 0
        assert error.returned_aid == 0
        assert error.returned_cid == 0

    def test_subtitle_mismatch_error_inheritance(self):
        """测试 SubtitleMismatchError 继承自 SubtitleValidationError。"""
        error = SubtitleMismatchError("Test error")

        # 验证继承关系
        assert isinstance(error, SubtitleMismatchError)
        assert isinstance(error, SubtitleValidationError)
        assert isinstance(error, Exception)

    def test_subtitle_mismatch_error_message_format(self):
        """测试 SubtitleMismatchError 的错误消息格式。"""
        # 创建带有详细信息的异常
        error = SubtitleMismatchError(
            message="Subtitle mismatch: expected aid=123456, cid=789012, got aid=111111, cid=222222",
            requested_aid=123456,
            requested_cid=789012,
            returned_aid=111111,
            returned_cid=222222,
        )

        # 验证消息格式
        assert "Subtitle mismatch" in str(error)
        assert "expected aid=123456" in str(error)
        assert "cid=789012" in str(error)
        assert "got aid=111111" in str(error)
        assert "cid=222222" in str(error)

        # 验证属性
        assert error.requested_aid == 123456
        assert error.requested_cid == 789012
        assert error.returned_aid == 111111
        assert error.returned_cid == 222222

    def test_subtitle_mismatch_error_can_be_raised(self):
        """测试 SubtitleMismatchError 可以被抛出和捕获。"""
        with pytest.raises(SubtitleMismatchError) as exc_info:
            raise SubtitleMismatchError(
                message="Test error",
                requested_aid=123456,
                requested_cid=789012,
                returned_aid=111111,
                returned_cid=222222,
            )

        # 验证捕获的异常
        error = exc_info.value
        assert str(error) == "Test error"
        assert error.requested_aid == 123456
        assert error.requested_cid == 789012
        assert error.returned_aid == 111111
        assert error.returned_cid == 222222

    def test_subtitle_mismatch_error_can_be_caught_as_subtitle_validation_error(self):
        """测试 SubtitleMismatchError 可以作为 SubtitleValidationError 被捕获。"""
        with pytest.raises(SubtitleValidationError):
            raise SubtitleMismatchError("Test error")

    def test_subtitle_mismatch_error_with_partial_mismatch(self):
        """测试部分不匹配的情况（只有 aid 或 cid 不匹配）。"""
        # 只有 aid 不匹配
        error1 = SubtitleMismatchError(
            message="Aid mismatch",
            requested_aid=123456,
            requested_cid=789012,
            returned_aid=111111,
            returned_cid=789012,  # cid 匹配
        )
        assert error1.requested_aid != error1.returned_aid
        assert error1.requested_cid == error1.returned_cid

        # 只有 cid 不匹配
        error2 = SubtitleMismatchError(
            message="Cid mismatch",
            requested_aid=123456,
            requested_cid=789012,
            returned_aid=123456,  # aid 匹配
            returned_cid=222222,
        )
        assert error2.requested_aid == error2.returned_aid
        assert error2.requested_cid != error2.returned_cid

    def test_subtitle_mismatch_error_with_zero_ids(self):
        """测试 ID 为 0 的情况（可能表示缺失）。"""
        # 返回的 ID 为 0（可能表示字幕数据缺少 aid/cid）
        error = SubtitleMismatchError(
            message="Missing aid/cid in subtitle data",
            requested_aid=123456,
            requested_cid=789012,
            returned_aid=0,
            returned_cid=0,
        )

        assert error.requested_aid == 123456
        assert error.requested_cid == 789012
        assert error.returned_aid == 0
        assert error.returned_cid == 0
