"""测试 V2 API 字幕验证增强功能。

验证需求：
- 9.1: 验证字幕的 aid/cid 是否匹配
- 9.3: 抛出 SubtitleMismatchError 异常
- 9.5: 记录详细信息
"""

import pytest
from unittest.mock import MagicMock, patch

from src.bilibili_extractor.modules.subtitle_fetcher import SubtitleFetcher
from src.bilibili_extractor.core.exceptions import SubtitleMismatchError


class TestV2APIValidationEnhancement:
    """测试 V2 API 字幕验证增强。"""
    
    def test_validate_subtitle_with_empty_body(self):
        """测试字幕内容为空时抛出异常。"""
        fetcher = SubtitleFetcher()
        
        # 字幕数据包含 aid/cid 但 body 为空
        subtitle_data = {
            'aid': 123456,
            'cid': 789012,
            'body': []
        }
        
        with pytest.raises(SubtitleMismatchError) as exc_info:
            fetcher._validate_subtitle(subtitle_data, 123456, 789012)
        
        assert "字幕内容为空" in str(exc_info.value)
    
    def test_validate_subtitle_with_valid_body(self):
        """测试字幕内容有效时通过验证。"""
        fetcher = SubtitleFetcher()
        
        # 字幕数据包含有效的 body
        subtitle_data = {
            'aid': 123456,
            'cid': 789012,
            'body': [
                {'from': 0, 'to': 2, 'content': '字幕1'},
                {'from': 2, 'to': 4, 'content': '字幕2'}
            ]
        }
        
        # 应该不抛出异常
        fetcher._validate_subtitle(subtitle_data, 123456, 789012)
    
    def test_validate_subtitle_mismatch_aid(self):
        """测试 aid 不匹配时抛出异常。"""
        fetcher = SubtitleFetcher()
        
        subtitle_data = {
            'aid': 999999,  # 不匹配的 aid
            'cid': 789012,
            'body': [{'from': 0, 'to': 2, 'content': '字幕'}]
        }
        
        with pytest.raises(SubtitleMismatchError) as exc_info:
            fetcher._validate_subtitle(subtitle_data, 123456, 789012)
        
        assert "字幕与视频不匹配" in str(exc_info.value)
        assert exc_info.value.returned_aid == 999999
    
    def test_validate_subtitle_mismatch_cid(self):
        """测试 cid 不匹配时抛出异常。"""
        fetcher = SubtitleFetcher()
        
        subtitle_data = {
            'aid': 123456,
            'cid': 999999,  # 不匹配的 cid
            'body': [{'from': 0, 'to': 2, 'content': '字幕'}]
        }
        
        with pytest.raises(SubtitleMismatchError) as exc_info:
            fetcher._validate_subtitle(subtitle_data, 123456, 789012)
        
        assert "字幕与视频不匹配" in str(exc_info.value)
        assert exc_info.value.returned_cid == 999999
