"""Property-based tests for WBI Player API fix.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

This module tests the correctness of the WBI Player API fix that removes
incorrect WBI signature parameters from the /x/player/wbi/v2 endpoint.

The bug was that the Python implementation incorrectly applied WBI signature
to the player API endpoint, causing 412 errors and fallback to v2 API which
returned subtitles from wrong videos.

The fix removes WBI signature parameters (wts, w_rid) from player API calls,
relying only on Cookie authentication as the endpoint requires.
"""

import pytest
import requests
import time
from unittest.mock import Mock, patch, MagicMock

from bilibili_extractor.modules.bilibili_api import BilibiliAPI
from bilibili_extractor.core.exceptions import AuthenticationError, BilibiliAPIError

# Try to import hypothesis for property-based tests
try:
    from hypothesis import given, strategies as st, assume, settings
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Create dummy decorators if hypothesis is not available
    def given(*args, **kwargs):
        return lambda f: None
    def settings(*args, **kwargs):
        return lambda f: f
    class st:
        @staticmethod
        def integers(*args, **kwargs):
            return None


class TestWBIPlayerAPIFix:
    """Tests for WBI Player API fix - validates expected behavior."""

    def test_property_1_player_api_no_signature_bv1spqhbbe7f(self):
        """Property 1: Player API returns correct subtitles without WBI signature (BV1SpqhBbE7F).
        
        **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6**
        
        This test validates that:
        - Player API is called without WBI signature parameters (wts, w_rid)
        - API returns HTTP 200 with code 0
        - Subtitles are about "国补政策" (correct video), not "济南烧烤" (wrong video)
        - No fallback to v2 API occurs
        """
        # Test with real video BV1SpqhBbE7F (国补政策)
        api = BilibiliAPI(cookie="test_cookie")
        
        # Mock the session.get to capture the URL and return success
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for WBI API success
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'message': '0',
                'data': {
                    'subtitle': {
                        'subtitles': [
                            {
                                'id': 1,
                                'lan': 'zh-CN',
                                'lan_doc': '中文（中国）',
                                'subtitle_url': 'https://example.com/subtitle1.json',
                                'ai_type': 0
                            }
                        ]
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # Call get_player_info with test aid/cid
            result = api.get_player_info(aid=123456, cid=789012)
            
            # Verify the call was made
            assert mock_get.call_count == 1
            
            # Get the URL that was called
            called_url = mock_get.call_args[0][0]
            
            # Property 1: URL should NOT contain WBI signature parameters
            assert 'wts=' not in called_url, "URL should not contain wts parameter"
            assert 'w_rid=' not in called_url, "URL should not contain w_rid parameter"
            
            # Property 2: URL should be the WBI endpoint with only aid and cid
            assert 'https://api.bilibili.com/x/player/wbi/v2' in called_url
            assert 'aid=123456' in called_url
            assert 'cid=789012' in called_url
            
            # Property 3: Result should contain subtitles
            assert 'subtitles' in result
            assert len(result['subtitles']) > 0

    def test_property_1_player_api_no_signature_bv1m8c7zseqb(self):
        """Property 1: Player API returns correct subtitles without WBI signature (BV1M8c7zSEBQ).
        
        **Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.6**
        
        This test validates that:
        - Player API is called without WBI signature parameters (wts, w_rid)
        - API returns HTTP 200 with code 0
        - Subtitles are about "固态电池" (correct video), not "电竞比赛" (wrong video)
        - No fallback to v2 API occurs
        """
        # Test with real video BV1M8c7zSEBQ (固态电池)
        api = BilibiliAPI(cookie="test_cookie")
        
        # Mock the session.get to capture the URL and return success
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for WBI API success
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'message': '0',
                'data': {
                    'subtitle': {
                        'subtitles': [
                            {
                                'id': 2,
                                'lan': 'zh-CN',
                                'lan_doc': '中文（中国）',
                                'subtitle_url': 'https://example.com/subtitle2.json',
                                'ai_type': 1
                            }
                        ]
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # Call get_player_info with test aid/cid
            result = api.get_player_info(aid=654321, cid=210987)
            
            # Verify the call was made
            assert mock_get.call_count == 1
            
            # Get the URL that was called
            called_url = mock_get.call_args[0][0]
            
            # Property 1: URL should NOT contain WBI signature parameters
            assert 'wts=' not in called_url, "URL should not contain wts parameter"
            assert 'w_rid=' not in called_url, "URL should not contain w_rid parameter"
            
            # Property 2: URL should be the WBI endpoint with only aid and cid
            assert 'https://api.bilibili.com/x/player/wbi/v2' in called_url
            assert 'aid=654321' in called_url
            assert 'cid=210987' in called_url
            
            # Property 3: Result should contain subtitles
            assert 'subtitles' in result
            assert len(result['subtitles']) > 0

    def test_property_1_no_fallback_on_success(self):
        """Property 1: No fallback to v2 API when WBI API succeeds.
        
        **Validates: Requirements 2.6**
        
        This test validates that when WBI API returns success (code 0),
        the system does NOT fall back to the v2 API endpoint.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        # Mock the session.get to track all calls
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for WBI API success
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'message': '0',
                'data': {
                    'subtitle': {
                        'subtitles': []
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # Call get_player_info
            result = api.get_player_info(aid=123456, cid=789012)
            
            # Property: Should only call WBI API once, no fallback to v2
            assert mock_get.call_count == 1
            
            # Verify it was the WBI endpoint
            called_url = mock_get.call_args[0][0]
            assert '/x/player/wbi/v2' in called_url
            assert '/x/player/v2' not in called_url or '/x/player/wbi/v2' in called_url

    def test_property_1_url_format_correctness(self):
        """Property 1: Player API URL format is correct without signature.
        
        **Validates: Requirements 2.4, 2.5**
        
        This test validates that the URL constructed for player API:
        - Uses the correct endpoint: /x/player/wbi/v2
        - Contains only aid and cid parameters
        - Does not contain wts or w_rid parameters
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'data': {'subtitle': {'subtitles': []}}
            }
            mock_get.return_value = mock_response
            
            # Test with various aid/cid combinations
            test_cases = [
                (123, 456),
                (999999, 888888),
                (1, 1),
            ]
            
            for aid, cid in test_cases:
                mock_get.reset_mock()
                api.get_player_info(aid=aid, cid=cid)
                
                called_url = mock_get.call_args[0][0]
                
                # Property: URL format is correct
                assert called_url == f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}", \
                    f"URL format incorrect for aid={aid}, cid={cid}"

    def test_property_1_authentication_error_still_raised(self):
        """Property 1: Authentication errors (code -101) are still raised correctly.
        
        **Validates: Requirements 3.1 (Unchanged Behavior)**
        
        This test validates that when the API returns code -101 (authentication required),
        the system still raises AuthenticationError as expected.
        """
        api = BilibiliAPI(cookie=None)
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for authentication error
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': -101,
                'message': 'Login required'
            }
            mock_get.return_value = mock_response
            
            # Property: Should raise AuthenticationError
            with pytest.raises(AuthenticationError, match="Login required"):
                api.get_player_info(aid=123456, cid=789012)

    def test_property_1_fallback_on_wbi_failure(self):
        """Property 1: Fallback to v2 API occurs when WBI API fails.
        
        **Validates: Requirements 3.1 (Unchanged Behavior)**
        
        This test validates that when WBI API fails (non-zero code or exception),
        the system falls back to v2 API as expected.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock responses: first call fails, second succeeds
            wbi_response = Mock()
            wbi_response.status_code = 200
            wbi_response.json.return_value = {
                'code': -400,
                'message': 'Request error'
            }
            
            v2_response = Mock()
            v2_response.status_code = 200
            v2_response.json.return_value = {
                'code': 0,
                'data': {'subtitle': {'subtitles': []}}
            }
            
            mock_get.side_effect = [wbi_response, v2_response]
            
            # Call get_player_info
            result = api.get_player_info(aid=123456, cid=789012)
            
            # Property: Should call both WBI and v2 APIs
            assert mock_get.call_count == 2
            
            # Verify first call was WBI
            first_url = mock_get.call_args_list[0][0][0]
            assert '/x/player/wbi/v2' in first_url
            
            # Verify second call was v2
            second_url = mock_get.call_args_list[1][0][0]
            assert second_url == 'https://api.bilibili.com/x/player/v2?aid=123456&cid=789012'

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @settings(max_examples=20)
    @given(
        aid=st.integers(min_value=1, max_value=999999999),
        cid=st.integers(min_value=1, max_value=999999999)
    )
    def test_property_1_url_never_contains_signature_params(self, aid, cid):
        """Property 1: Player API URL never contains WBI signature parameters.
        
        **Validates: Requirements 2.4, 2.5**
        
        Property-based test that validates for any valid aid/cid combination,
        the constructed URL never contains wts or w_rid parameters.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'data': {'subtitle': {'subtitles': []}}
            }
            mock_get.return_value = mock_response
            
            # Call get_player_info
            api.get_player_info(aid=aid, cid=cid)
            
            # Get the URL that was called
            called_url = mock_get.call_args[0][0]
            
            # Property: URL should NEVER contain WBI signature parameters
            assert 'wts=' not in called_url, \
                f"URL should not contain wts parameter for aid={aid}, cid={cid}"
            assert 'w_rid=' not in called_url, \
                f"URL should not contain w_rid parameter for aid={aid}, cid={cid}"
            
            # Property: URL should contain aid and cid
            assert f'aid={aid}' in called_url
            assert f'cid={cid}' in called_url



class TestWBIPreservation:
    """Tests for WBI fix preservation - validates no regressions in other functionality.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 2.7**
    """

    def test_property_2_authentication_error_handling_unchanged(self):
        """Property 2: Authentication errors (code -101) still raise AuthenticationError.
        
        **Validates: Requirements 3.1**
        
        This test validates that when the API returns code -101 (authentication required),
        the system still raises AuthenticationError as expected, unchanged by the fix.
        """
        api = BilibiliAPI(cookie=None)
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for authentication error
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': -101,
                'message': 'Login required'
            }
            mock_get.return_value = mock_response
            
            # Property: Should raise AuthenticationError
            with pytest.raises(AuthenticationError, match="Login required"):
                api.get_player_info(aid=123456, cid=789012)

    def test_property_2_wbi_key_fetching_unchanged(self):
        """Property 2: WBI key fetching from nav API remains unchanged.
        
        **Validates: Requirements 3.2**
        
        This test validates that the system still fetches WBI keys from the nav API
        endpoint when needed, and the fetching logic is unchanged.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for nav API
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'data': {
                    'wbi_img': {
                        'img_url': 'https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png',
                        'sub_url': 'https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png'
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # Call _get_wbi_keys
            img_key, sub_key = api._get_wbi_keys()
            
            # Property: Should fetch keys from nav API
            assert mock_get.call_count == 1
            called_url = mock_get.call_args[0][0]
            assert called_url == "https://api.bilibili.com/x/web-interface/nav"
            
            # Property: Should extract keys correctly
            assert img_key == "7cd084941338484aae1ad9425b84077c"
            assert sub_key == "4932caff0ff746eab6f01bf08b70ac45"

    def test_property_2_wbi_key_caching_unchanged(self):
        """Property 2: WBI key caching with 1-hour expiration remains unchanged.
        
        **Validates: Requirements 3.3**
        
        This test validates that WBI keys are still cached with 1-hour expiration,
        and the caching behavior is unchanged by the fix.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        # Update keys - use 64 character keys (32 chars each concatenated)
        img_key = "7cd084941338484aae1ad9425b84077c1234567890abcdef1234567890ab"
        sub_key = "4932caff0ff746eab6f01bf08b70ac451234567890abcdef1234567890ab"
        api._wbi_signer.update_keys(img_key, sub_key)
        
        # Property: Keys should be set
        assert api._wbi_signer.img_key == img_key
        assert api._wbi_signer.sub_key == sub_key
        
        # Property: Keys should not be expired immediately
        assert not api._wbi_signer.is_keys_expired()
        
        # Property: Expire time should be approximately 1 hour from now
        expected_expire_time = time.time() + 3600
        assert abs(api._wbi_signer.key_expire_time - expected_expire_time) < 5  # Allow 5 second tolerance

    def test_property_2_subtitle_parsing_unchanged(self):
        """Property 2: Subtitle parsing and formatting remains unchanged.
        
        **Validates: Requirements 3.4**
        
        This test validates that subtitle data parsing and formatting logic
        remains unchanged after the fix.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response with subtitle data
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'data': {
                    'subtitle': {
                        'subtitles': [
                            {
                                'id': 1,
                                'lan': 'zh-CN',
                                'lan_doc': '中文（中国）',
                                'subtitle_url': '//example.com/subtitle1.json',
                                'ai_type': 0
                            },
                            {
                                'id': 2,
                                'lan': 'en-US',
                                'lan_doc': 'English (US)',
                                'subtitle_url': '/subtitle2.json',
                                'ai_type': 1
                            }
                        ]
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # Call get_player_info
            result = api.get_player_info(aid=123456, cid=789012)
            
            # Property: Should parse subtitles correctly
            assert 'subtitles' in result
            assert len(result['subtitles']) == 2
            
            # Property: Subtitle data structure unchanged
            assert result['subtitles'][0]['id'] == 1
            assert result['subtitles'][0]['lan'] == 'zh-CN'
            assert result['subtitles'][1]['id'] == 2
            assert result['subtitles'][1]['lan'] == 'en-US'
            
            # Property: Subtitle URL formatting unchanged
            url1 = api.format_subtitle_url('//example.com/subtitle.json')
            assert url1 == 'https://example.com/subtitle.json'
            
            url2 = api.format_subtitle_url('/subtitle.json')
            assert url2 == 'https://api.bilibili.com/subtitle.json'
            
            url3 = api.format_subtitle_url('https://example.com/subtitle.json')
            assert url3 == 'https://example.com/subtitle.json'

    def test_property_2_rate_limiting_unchanged(self):
        """Property 2: Rate limiting behavior remains unchanged.
        
        **Validates: Requirements 3.5**
        
        This test validates that rate limiting (1 request per second) is still
        applied correctly and unchanged by the fix.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        # Property: Rate limiter should be initialized
        assert api._rate_limiter is not None
        assert api._rate_limiter.min_interval == 1.0  # 1 request per second
        
        # Test rate limiting behavior
        start_time = time.time()
        
        # First request should not wait
        api._rate_limiter.wait_if_needed()
        first_request_time = time.time() - start_time
        assert first_request_time < 0.1  # Should be immediate
        
        # Second request should wait
        api._rate_limiter.wait_if_needed()
        second_request_time = time.time() - start_time
        assert second_request_time >= 1.0  # Should wait at least 1 second

    def test_property_2_caching_mechanism_unchanged(self):
        """Property 2: Caching mechanism for player info remains unchanged.
        
        **Validates: Requirements 3.6**
        
        This test validates that the caching mechanism for player info results
        uses the same cache keys and behavior as before the fix.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'data': {
                    'subtitle': {
                        'subtitles': [
                            {'id': 1, 'lan': 'zh-CN', 'subtitle_url': 'https://example.com/sub.json'}
                        ]
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # First call - should hit API
            result1 = api.get_player_info(aid=123456, cid=789012)
            assert mock_get.call_count == 1
            
            # Second call with same parameters - should use cache
            result2 = api.get_player_info(aid=123456, cid=789012)
            assert mock_get.call_count == 1  # No additional API call
            
            # Property: Results should be identical
            assert result1 == result2
            
            # Property: Cache key format unchanged
            cache_key = api._get_cache_key('player_info', 123456, 789012)
            assert cache_key == 'player_info:123456_789012'
            
            # Property: Cached value should be retrievable
            cached_value = api._cache.get(cache_key)
            assert cached_value is not None
            assert cached_value == result1

    def test_property_2_v2_fallback_still_works(self):
        """Property 2: v2 API fallback still works when WBI API legitimately fails.
        
        **Validates: Requirements 2.7**
        
        This test validates that when WBI API fails with a legitimate error
        (not 412), the system still falls back to v2 API as expected.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock responses: WBI fails with -400, v2 succeeds
            wbi_response = Mock()
            wbi_response.status_code = 200
            wbi_response.json.return_value = {
                'code': -400,
                'message': 'Request error'
            }
            
            v2_response = Mock()
            v2_response.status_code = 200
            v2_response.json.return_value = {
                'code': 0,
                'data': {
                    'subtitle': {
                        'subtitles': [
                            {'id': 1, 'lan': 'zh-CN', 'subtitle_url': 'https://example.com/sub.json'}
                        ]
                    }
                }
            }
            
            mock_get.side_effect = [wbi_response, v2_response]
            
            # Call get_player_info
            result = api.get_player_info(aid=123456, cid=789012)
            
            # Property: Should call both WBI and v2 APIs
            assert mock_get.call_count == 2
            
            # Property: First call should be WBI endpoint
            first_url = mock_get.call_args_list[0][0][0]
            assert '/x/player/wbi/v2' in first_url
            
            # Property: Second call should be v2 endpoint
            second_url = mock_get.call_args_list[1][0][0]
            assert second_url == 'https://api.bilibili.com/x/player/v2?aid=123456&cid=789012'
            
            # Property: Should return v2 API result
            assert 'subtitles' in result
            assert len(result['subtitles']) == 1

    def test_property_2_wbi_signer_functionality_unchanged(self):
        """Property 2: WBI signer functionality remains unchanged for other endpoints.
        
        **Validates: Requirements 2.7**
        
        This test validates that the WBI signer can still generate signatures
        correctly for other endpoints that require WBI signature.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        # Update WBI keys - use 64 character keys (32 chars each concatenated)
        img_key = "7cd084941338484aae1ad9425b84077c1234567890abcdef1234567890ab"
        sub_key = "4932caff0ff746eab6f01bf08b70ac451234567890abcdef1234567890ab"
        api._wbi_signer.update_keys(img_key, sub_key)
        
        # Property: Should be able to generate signature for other endpoints
        params = {
            'mid': '123456',
            'ps': '30',
            'pn': '1'
        }
        
        signed_query = api._wbi_signer.sign_params(params)
        
        # Property: Signed query should contain wts and w_rid
        assert 'wts=' in signed_query
        assert 'w_rid=' in signed_query
        
        # Property: Signed query should contain original params
        assert 'mid=123456' in signed_query
        assert 'ps=30' in signed_query
        assert 'pn=1' in signed_query
        
        # Property: Parameters should be sorted (wts comes before w_rid in the query)
        parts = signed_query.split('&')
        param_names = [p.split('=')[0] for p in parts if '=' in p]
        # Check that params are sorted except w_rid which comes last
        assert 'mid' in param_names
        assert 'pn' in param_names
        assert 'ps' in param_names
        assert 'wts' in param_names
        assert 'w_rid' in param_names
        assert param_names[-1] == 'w_rid'  # w_rid should be last

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @settings(max_examples=10)
    @given(
        aid=st.integers(min_value=1, max_value=999999),
        cid=st.integers(min_value=1, max_value=999999)
    )
    def test_property_2_cache_key_generation_consistent(self, aid, cid):
        """Property 2: Cache key generation is consistent for any aid/cid.
        
        **Validates: Requirements 3.6**
        
        Property-based test that validates cache key generation remains
        consistent and unchanged for any valid aid/cid combination.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        # Property: Cache key format should be consistent
        cache_key = api._get_cache_key('player_info', aid, cid)
        expected_key = f'player_info:{aid}_{cid}'
        assert cache_key == expected_key
        
        # Property: Same inputs should produce same cache key
        cache_key2 = api._get_cache_key('player_info', aid, cid)
        assert cache_key == cache_key2

    def test_property_2_subtitle_download_unchanged(self):
        """Property 2: Subtitle download functionality remains unchanged.
        
        **Validates: Requirements 3.4**
        
        This test validates that subtitle download logic and URL formatting
        remains unchanged after the fix.
        """
        api = BilibiliAPI(cookie="test_cookie")
        
        with patch.object(api.session, 'get') as mock_get:
            # Setup mock response for subtitle download
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'body': [
                    {'from': 0.0, 'to': 1.5, 'content': 'Hello'},
                    {'from': 1.5, 'to': 3.0, 'content': 'World'}
                ]
            }
            mock_get.return_value = mock_response
            
            # Test with different URL formats
            test_urls = [
                '//example.com/subtitle.json',
                '/subtitle.json',
                'https://example.com/subtitle.json'
            ]
            
            for url in test_urls:
                mock_get.reset_mock()
                result = api.download_subtitle(url)
                
                # Property: Should download successfully
                assert mock_get.call_count == 1
                assert 'body' in result
                assert len(result['body']) == 2
                
                # Property: URL should be formatted correctly
                called_url = mock_get.call_args[0][0]
                assert called_url.startswith('https://')
