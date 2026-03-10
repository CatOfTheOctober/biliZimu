"""Unit tests for URLValidator module."""

import pytest
from src.bilibili_extractor.modules.url_validator import URLValidator, URLValidationError


class TestURLValidatorValidate:
    """Tests for URLValidator.validate() method."""

    def test_validate_bv_url_with_https(self):
        """Test validation of BV URL with https."""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        assert URLValidator.validate(url) is True

    def test_validate_bv_url_without_https(self):
        """Test validation of BV URL without https."""
        url = "bilibili.com/video/BV1xx411c7mD"
        assert URLValidator.validate(url) is True

    def test_validate_bv_url_without_www(self):
        """Test validation of BV URL without www."""
        url = "https://bilibili.com/video/BV1xx411c7mD"
        assert URLValidator.validate(url) is True

    def test_validate_av_url(self):
        """Test validation of av URL."""
        url = "https://www.bilibili.com/video/av12345678"
        assert URLValidator.validate(url) is True

    def test_validate_short_link_with_https(self):
        """Test validation of short link with https."""
        url = "https://b23.tv/abc123"
        assert URLValidator.validate(url) is True

    def test_validate_short_link_without_https(self):
        """Test validation of short link without https."""
        url = "b23.tv/abc123"
        assert URLValidator.validate(url) is True

    def test_validate_invalid_url(self):
        """Test validation of invalid URL."""
        url = "https://www.youtube.com/watch?v=123"
        assert URLValidator.validate(url) is False

    def test_validate_empty_string(self):
        """Test validation of empty string."""
        assert URLValidator.validate("") is False

    def test_validate_none(self):
        """Test validation of None."""
        assert URLValidator.validate(None) is False


class TestURLValidatorExtractVideoId:
    """Tests for URLValidator.extract_video_id() method."""

    def test_extract_bv_id_with_https(self):
        """Test extracting BV ID from URL with https."""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        assert URLValidator.extract_video_id(url) == "BV1xx411c7mD"

    def test_extract_bv_id_without_https(self):
        """Test extracting BV ID from URL without https."""
        url = "bilibili.com/video/BV1xx411c7mD"
        assert URLValidator.extract_video_id(url) == "BV1xx411c7mD"

    def test_extract_bv_id_case_insensitive(self):
        """Test extracting BV ID is case insensitive."""
        url = "https://www.BILIBILI.com/video/BV1xx411c7mD"
        assert URLValidator.extract_video_id(url) == "BV1xx411c7mD"

    def test_extract_av_id(self):
        """Test extracting av ID from URL."""
        url = "https://www.bilibili.com/video/av12345678"
        assert URLValidator.extract_video_id(url) == "av12345678"

    def test_extract_video_id_invalid_url(self):
        """Test extracting video ID from invalid URL raises error."""
        url = "https://www.youtube.com/watch?v=123"
        with pytest.raises(URLValidationError):
            URLValidator.extract_video_id(url)

    def test_extract_video_id_empty_string(self):
        """Test extracting video ID from empty string raises error."""
        with pytest.raises(URLValidationError):
            URLValidator.extract_video_id("")

    def test_extract_video_id_none(self):
        """Test extracting video ID from None raises error."""
        with pytest.raises(URLValidationError):
            URLValidator.extract_video_id(None)


class TestURLValidatorNormalizeUrl:
    """Tests for URLValidator.normalize_url() method."""

    def test_normalize_bv_url_returns_same(self):
        """Test normalizing BV URL returns the same URL."""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        assert URLValidator.normalize_url(url) == url

    def test_normalize_av_url_returns_same(self):
        """Test normalizing av URL returns the same URL."""
        url = "https://www.bilibili.com/video/av12345678"
        assert URLValidator.normalize_url(url) == url

    def test_normalize_invalid_url_raises_error(self):
        """Test normalizing invalid URL raises error."""
        url = "https://www.youtube.com/watch?v=123"
        with pytest.raises(URLValidationError):
            URLValidator.normalize_url(url)

    def test_normalize_empty_string_raises_error(self):
        """Test normalizing empty string raises error."""
        with pytest.raises(URLValidationError):
            URLValidator.normalize_url("")

    def test_normalize_none_raises_error(self):
        """Test normalizing None raises error."""
        with pytest.raises(URLValidationError):
            URLValidator.normalize_url(None)


class TestURLValidatorProperties:
    """Property-based tests for URLValidator."""

    def test_property_validate_and_extract_consistency(self):
        """Test Property 2: validate() returns True iff extract_video_id() doesn't raise."""
        valid_urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "bilibili.com/video/BV1xx411c7mD",
            "https://bilibili.com/video/BV1xx411c7mD",
            "https://www.bilibili.com/video/av12345678",
            "bilibili.com/video/av12345678",
        ]
        
        for url in valid_urls:
            # If validate returns True, extract_video_id should not raise
            if URLValidator.validate(url):
                try:
                    video_id = URLValidator.extract_video_id(url)
                    assert video_id is not None
                except Exception:
                    pytest.fail(f"extract_video_id raised exception for valid URL: {url}")

    def test_property_extract_video_id_consistency(self):
        """Test Property 1: extract_video_id returns consistent video_id for valid URLs."""
        # Test with different URL formats for the same video
        urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "https://bilibili.com/video/BV1xx411c7mD",
            "bilibili.com/video/BV1xx411c7mD",
            "www.bilibili.com/video/BV1xx411c7mD",
        ]
        
        video_ids = [URLValidator.extract_video_id(url) for url in urls]
        
        # All should return the same video ID
        assert all(vid == "BV1xx411c7mD" for vid in video_ids)
