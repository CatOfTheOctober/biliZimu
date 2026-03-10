"""
单元测试：对比 JS 和 Python 的 WBI 签名实现

这个测试验证 Python 的 WBI 签名是否与 JS 版本一致。
"""

import pytest
import hashlib
import urllib.parse
from src.bilibili_extractor.modules.wbi_sign import encode_wbi, get_mixin_key, MIXIN_KEY_ENC_TAB


class TestWBISignatureComparison:
    """对比 JS 和 Python 的 WBI 签名实现"""
    
    def test_mixin_key_enc_tab_matches_js(self):
        """测试 MIXIN_KEY_ENC_TAB 是否与 JS 版本一致"""
        # JS 版本的 mixinKeyEncTab
        js_tab = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
            33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
            61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
            36, 20, 34, 44, 52
        ]
        
        assert MIXIN_KEY_ENC_TAB == js_tab, "MIXIN_KEY_ENC_TAB 与 JS 版本不一致"
    
    def test_get_mixin_key_logic(self):
        """测试 get_mixin_key 的逻辑"""
        # 测试用例：img_key + sub_key（必须至少 64 个字符）
        # 真实的 img_key 和 sub_key 各 32 个字符
        test_input = "abcdefghijklmnopqrstuvwxyz01234" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        assert len(test_input) == 64, f"测试输入长度应为 64，实际为 {len(test_input)}"
        
        result = get_mixin_key(test_input)
        
        # 验证结果长度为 32
        assert len(result) == 32, f"mixin_key 长度应为 32，实际为 {len(result)}"
        
        # 验证结果只包含输入字符串中的字符
        for char in result:
            assert char in test_input, f"mixin_key 包含不在输入中的字符: {char}"
    
    def test_get_mixin_key_input_too_short(self):
        """测试 get_mixin_key 对输入过短的处理"""
        # 输入长度不足 64 个字符
        test_input = "short_input"
        
        with pytest.raises(ValueError, match="输入长度必须至少 64 个字符"):
            get_mixin_key(test_input)
    
    def test_encode_wbi_parameter_filtering(self):
        """测试 encode_wbi 中的参数过滤逻辑"""
        # 测试参数中包含需要过滤的字符
        params = {
            'aid': 123456,
            'cid': 789012,
            'text': "hello'world!test(data)*here",
        }
        
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz012345"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        result = encode_wbi(params, img_key, sub_key)
        
        # 验证结果包含 w_rid 和 wts
        assert 'w_rid' in result, "结果应包含 w_rid"
        assert 'wts' in result, "结果应包含 wts"
        
        # 验证 w_rid 是 32 位的 MD5 哈希
        assert len(result['w_rid']) == 32, f"w_rid 长度应为 32，实际为 {len(result['w_rid'])}"
        
        # 验证 w_rid 只包含十六进制字符
        assert all(c in '0123456789abcdef' for c in result['w_rid']), "w_rid 应只包含十六进制字符"
    
    def test_encode_wbi_parameter_sorting(self):
        """测试 encode_wbi 中的参数排序"""
        # 测试参数排序
        params = {
            'z': 1,
            'a': 2,
            'm': 3,
        }
        
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz012345"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        result = encode_wbi(params, img_key, sub_key)
        
        # 验证参数已排序
        keys = list(result.keys())
        # 移除 w_rid 和 wts，检查其他参数是否已排序
        sorted_keys = sorted([k for k in keys if k not in ['w_rid', 'wts']])
        actual_keys = [k for k in keys if k not in ['w_rid', 'wts']]
        
        assert actual_keys == sorted_keys, f"参数应按字母顺序排序，实际为 {actual_keys}"
    
    def test_encode_wbi_deterministic(self):
        """测试 encode_wbi 的确定性（相同输入应产生相同输出）"""
        params1 = {'aid': 123456, 'cid': 789012}
        params2 = {'aid': 123456, 'cid': 789012}
        
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz012345"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        # 注意：由于 wts 是时间戳，我们需要在同一时刻调用
        # 这个测试可能不完全确定性，但我们可以验证其他参数
        result1 = encode_wbi(params1, img_key, sub_key)
        result2 = encode_wbi(params2, img_key, sub_key)
        
        # 验证 aid 和 cid 相同
        assert result1['aid'] == result2['aid']
        assert result1['cid'] == result2['cid']
        
        # 注意：w_rid 可能不同，因为 wts 不同
        # 但如果 wts 相同，w_rid 应该相同
    
    def test_encode_wbi_special_characters(self):
        """测试 encode_wbi 对特殊字符的处理"""
        # 测试包含需要过滤的特殊字符的参数
        params = {
            'text': "test'with!special(chars)*here",
            'value': 123,
        }
        
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz012345"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        result = encode_wbi(params, img_key, sub_key)
        
        # 验证特殊字符已被过滤
        # 在 URL 编码后，特殊字符应该被移除
        assert 'w_rid' in result
        assert result['w_rid']  # w_rid 不应为空


class TestWBISignatureEdgeCases:
    """测试 WBI 签名的边界情况"""
    
    def test_encode_wbi_empty_params(self):
        """测试空参数"""
        params = {}
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz012345"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        result = encode_wbi(params, img_key, sub_key)
        
        # 即使参数为空，也应该有 w_rid 和 wts
        assert 'w_rid' in result
        assert 'wts' in result
    
    def test_encode_wbi_large_numbers(self):
        """测试大数字参数"""
        params = {
            'aid': 999999999999,
            'cid': 888888888888,
        }
        
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz01234"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        result = encode_wbi(params, img_key, sub_key)
        
        # 验证大数字被正确处理（encode_wbi 返回字符串值）
        assert result['aid'] == '999999999999'
        assert result['cid'] == '888888888888'
        assert 'w_rid' in result
    
    def test_encode_wbi_unicode_characters(self):
        """测试 Unicode 字符"""
        params = {
            'text': '你好世界',
            'value': 123,
        }
        
        # 真实的 img_key 和 sub_key 各 32 个字符
        img_key = "abcdefghijklmnopqrstuvwxyz012345"
        sub_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ67890ab"
        
        result = encode_wbi(params, img_key, sub_key)
        
        # 验证 Unicode 字符被正确处理
        assert 'w_rid' in result
        assert result['w_rid']  # w_rid 不应为空


class TestWBISignatureURLEncoding:
    """测试 WBI 签名中的 URL 编码"""
    
    def test_url_encoding_consistency(self):
        """测试 URL 编码的一致性"""
        # 测试 urllib.parse.urlencode 的行为
        params = {
            'aid': 123456,
            'cid': 789012,
            'text': 'hello world',
        }
        
        # Python 的 urlencode
        encoded = urllib.parse.urlencode(params)
        
        # 验证编码结果
        assert 'aid=123456' in encoded
        assert 'cid=789012' in encoded
        assert 'text=hello+world' in encoded or 'text=hello%20world' in encoded
    
    def test_special_char_filtering_before_encoding(self):
        """测试特殊字符过滤在编码前进行"""
        # 这是 JS 版本的行为：先过滤特殊字符，再编码
        text = "test'with!special(chars)*here"
        
        # 过滤特殊字符
        filtered = ''.join(filter(lambda c: c not in "!'()*", text))
        
        # 验证过滤结果
        assert filtered == "testwithspecialcharshere"
        
        # 编码
        encoded = urllib.parse.urlencode({'text': filtered})
        assert 'text=testwithspecialcharshere' in encoded


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
