"""
集成测试：验证 AI 字幕获取修复

这个测试验证新的 get_subtitle_with_ai_fallback() 函数是否能正确获取 AI 字幕。
测试完全复制了 JS 版本的逻辑。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.bilibili_extractor.modules.bilibili_api import BilibiliAPI


class TestAISubtitleFix:
    """测试 AI 字幕获取修复"""
    
    @pytest.fixture
    def api(self):
        """创建 BilibiliAPI 实例"""
        return BilibiliAPI(cookie="test_cookie")
    
    def test_headers_include_wbi_ua(self, api):
        """测试请求头是否包含 X-Wbi-UA"""
        assert 'X-Wbi-UA' in api.session.headers
        assert api.session.headers['X-Wbi-UA'] == 'Win32.Chrome.109.0.0.0'
    
    def test_headers_include_all_required_fields(self, api):
        """测试请求头是否包含所有必需字段"""
        required_headers = [
            'User-Agent',
            'Accept',
            'Accept-Language',
            'Origin',
            'Referer',
            'Cache-Control',
            'Connection',
            'Pragma',
            'X-Wbi-UA',
        ]
        
        for header in required_headers:
            assert header in api.session.headers, f"缺少请求头: {header}"
    
    def test_format_time_conversion(self, api):
        """测试时间格式化函数"""
        # 测试各种时间值
        test_cases = [
            (0, "00:00:00,000"),
            (1.5, "00:00:01,500"),
            (60, "00:01:00,000"),
            (3661.123, "01:01:01,123"),
        ]
        
        for seconds, expected in test_cases:
            result = api._format_time(seconds)
            assert result == expected, f"时间格式化错误: {seconds}s -> {result} (期望: {expected})"
    
    def test_format_subtitles_to_srt(self, api):
        """测试字幕格式化为 SRT 格式"""
        subtitles = [
            {'from': 0, 'to': 2, 'content': '第一条字幕'},
            {'from': 2, 'to': 5, 'content': '第二条字幕'},
        ]
        
        result = api._format_subtitles_to_srt(subtitles)
        
        # 验证 SRT 格式
        lines = result.strip().split('\n')
        assert lines[0] == '1'  # 第一条字幕序号
        assert lines[1] == '00:00:00,000 --> 00:00:02,000'  # 时间戳
        assert lines[2] == '第一条字幕'  # 内容
        assert lines[4] == '2'  # 第二条字幕序号
    
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.get_player_info')
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.download_subtitle')
    def test_get_subtitle_with_ai_fallback_success(self, mock_download, mock_player_info, api):
        """测试成功获取 AI 字幕的流程"""
        # 模拟播放器信息响应
        mock_player_info.return_value = {
            'subtitles': [
                {
                    'lan': 'ai-zh',
                    'lan_doc': '自动生成字幕',
                    'subtitle_url': 'https://example.com/subtitle.json'
                }
            ],
            'subtitle_data': {}
        }
        
        # 模拟字幕下载响应
        mock_download.return_value = {
            'body': [
                {'from': 0, 'to': 2, 'content': '测试字幕'},
            ]
        }
        
        # 调用函数
        result = api.get_subtitle_with_ai_fallback(
            aid=123456,
            cid=789012,
            bvid='BV1234567890'
        )
        
        # 验证结果
        assert result['success'] is True
        assert result['metadata']['lan'] == 'ai-zh'
        assert len(result['subtitles']) == 1
        assert '测试字幕' in result['subtitle_text']
    
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.get_player_info')
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.get_ai_subtitle_url')
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.download_subtitle')
    def test_get_subtitle_with_ai_fallback_empty_url(self, mock_download, mock_ai_url, mock_player_info, api):
        """测试字幕 URL 为空时的 AI 字幕 API 调用"""
        # 模拟播放器信息响应（URL 为空）
        mock_player_info.return_value = {
            'subtitles': [
                {
                    'lan': 'ai-zh',
                    'lan_doc': '自动生成字幕',
                    'subtitle_url': None  # URL 为空
                }
            ],
            'subtitle_data': {}
        }
        
        # 模拟 AI 字幕 API 响应
        mock_ai_url.return_value = 'https://example.com/ai_subtitle.json'
        
        # 模拟字幕下载响应
        mock_download.return_value = {
            'body': [
                {'from': 0, 'to': 2, 'content': 'AI 生成的字幕'},
            ]
        }
        
        # 调用函数
        result = api.get_subtitle_with_ai_fallback(
            aid=123456,
            cid=789012,
            bvid='BV1234567890'
        )
        
        # 验证结果
        assert result['success'] is True
        # 验证 AI 字幕 API 被调用
        mock_ai_url.assert_called_once_with(123456, 789012)
        assert 'AI 生成的字幕' in result['subtitle_text']
    
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.get_player_info')
    def test_get_subtitle_with_ai_fallback_no_subtitles(self, mock_player_info, api):
        """测试没有字幕的情况"""
        # 模拟播放器信息响应（没有字幕）
        mock_player_info.return_value = {
            'subtitles': [],
            'subtitle_data': {}
        }
        
        # 调用函数
        result = api.get_subtitle_with_ai_fallback(
            aid=123456,
            cid=789012,
            bvid='BV1234567890'
        )
        
        # 验证结果
        assert result['success'] is False
        assert '没有可用字幕' in result['message']
    
    @patch('src.bilibili_extractor.modules.bilibili_api.BilibiliAPI.get_player_info')
    def test_get_subtitle_with_ai_fallback_prefers_ai_zh(self, mock_player_info, api):
        """测试优先选择 ai-zh 字幕"""
        # 模拟播放器信息响应（多个字幕）
        mock_player_info.return_value = {
            'subtitles': [
                {
                    'lan': 'zh-CN',
                    'lan_doc': '中文',
                    'subtitle_url': 'https://example.com/zh.json'
                },
                {
                    'lan': 'ai-zh',
                    'lan_doc': '自动生成字幕',
                    'subtitle_url': 'https://example.com/ai_zh.json'
                },
                {
                    'lan': 'en-US',
                    'lan_doc': 'English',
                    'subtitle_url': 'https://example.com/en.json'
                }
            ],
            'subtitle_data': {}
        }
        
        with patch.object(api, 'download_subtitle') as mock_download:
            mock_download.return_value = {
                'body': [
                    {'from': 0, 'to': 2, 'content': 'AI 字幕'},
                ]
            }
            
            # 调用函数
            result = api.get_subtitle_with_ai_fallback(
                aid=123456,
                cid=789012,
                bvid='BV1234567890'
            )
            
            # 验证选择了 ai-zh 字幕
            assert result['metadata']['lan'] == 'ai-zh'
            # 验证下载的是 ai-zh 字幕 URL
            mock_download.assert_called_once_with('https://example.com/ai_zh.json')


class TestRequestHeadersCompliance:
    """测试请求头是否符合 JS 版本的标准"""
    
    @pytest.fixture
    def api(self):
        """创建 BilibiliAPI 实例"""
        return BilibiliAPI(cookie="test_cookie")
    
    def test_user_agent_matches_js_version(self, api):
        """测试 User-Agent 是否与 JS 版本一致"""
        ua = api.session.headers['User-Agent']
        # 应该包含 Chrome 标识
        assert 'Chrome' in ua
        assert 'Windows' in ua or 'Win64' in ua
    
    def test_accept_language_includes_chinese(self, api):
        """测试 Accept-Language 是否包含中文"""
        accept_lang = api.session.headers['Accept-Language']
        assert 'zh-CN' in accept_lang
    
    def test_origin_is_bilibili(self, api):
        """测试 Origin 是否为 bilibili.com"""
        origin = api.session.headers['Origin']
        assert 'bilibili.com' in origin
    
    def test_referer_is_bilibili(self, api):
        """测试 Referer 是否为 bilibili.com"""
        referer = api.session.headers['Referer']
        assert 'bilibili.com' in referer


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
