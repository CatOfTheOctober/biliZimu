"""URL validation and parsing for Bilibili videos."""

import re
import requests
from typing import Optional


class URLValidationError(Exception):
    """Exception raised when URL validation fails."""
    pass


class URLValidator:
    """Validate and parse Bilibili video URLs."""

    # Regex patterns for different URL formats
    BV_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[a-zA-Z0-9]+)',
        re.IGNORECASE
    )
    AV_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/av(\d+)',
        re.IGNORECASE
    )
    SHORT_LINK_PATTERN = re.compile(
        r'(?:https?://)?b23\.tv/([a-zA-Z0-9]+)',
        re.IGNORECASE
    )

    @staticmethod
    def validate(url: str) -> bool:
        """Validate if URL is a valid Bilibili video URL.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check if it matches any of the supported patterns
        if URLValidator.BV_PATTERN.search(url):
            return True
        if URLValidator.AV_PATTERN.search(url):
            return True
        if URLValidator.SHORT_LINK_PATTERN.search(url):
            return True
        
        return False

    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID (BV or av number) from URL.

        Args:
            url: Bilibili video URL

        Returns:
            Video ID string (BV号 or av号)

        Raises:
            URLValidationError: If URL is invalid or video ID cannot be extracted
        """
        if not url or not isinstance(url, str):
            raise URLValidationError("URL must be a non-empty string")
        
        url = url.strip()
        
        # Try to match BV format
        bv_match = URLValidator.BV_PATTERN.search(url)
        if bv_match:
            return bv_match.group(1)
        
        # Try to match av format
        av_match = URLValidator.AV_PATTERN.search(url)
        if av_match:
            return f"av{av_match.group(1)}"
        
        # Try to match short link - need to normalize first
        short_match = URLValidator.SHORT_LINK_PATTERN.search(url)
        if short_match:
            try:
                normalized_url = URLValidator.normalize_url(url)
                return URLValidator.extract_video_id(normalized_url)
            except Exception as e:
                raise URLValidationError(f"Failed to resolve short link: {str(e)}")
        
        raise URLValidationError(
            f"Invalid Bilibili URL format. Supported formats: "
            f"bilibili.com/video/BV*, bilibili.com/video/av*, b23.tv/*"
        )

    @staticmethod
    def extract_page_number(url: str) -> int:
        """Extract page number from URL.
        
        For multi-page videos, the URL may contain a 'p' parameter (e.g., ?p=2).
        If no page parameter is found, returns 1 (first page).
        
        Args:
            url: Bilibili video URL
            
        Returns:
            Page number (1-indexed)
        """
        if not url or not isinstance(url, str):
            return 1
        
        # Extract p parameter from URL
        # Examples:
        # - https://www.bilibili.com/video/BV1xx411c7mD?p=2
        # - https://www.bilibili.com/video/BV1xx411c7mD/?p=2&other=value
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Get 'p' parameter
            if 'p' in query_params:
                page_str = query_params['p'][0]
                page_num = int(page_str)
                return max(1, page_num)  # Ensure at least 1
        except (ValueError, IndexError, KeyError):
            pass
        
        return 1

    @staticmethod
    def normalize_url(url: str) -> str:
        """Convert short links to standard URLs.

        Args:
            url: Bilibili video URL (may be short link)

        Returns:
            Normalized standard URL

        Raises:
            URLValidationError: If URL cannot be normalized
        """
        if not url or not isinstance(url, str):
            raise URLValidationError("URL must be a non-empty string")
        
        url = url.strip()
        
        # If it's already a standard bilibili.com URL, return as-is
        if URLValidator.BV_PATTERN.search(url) or URLValidator.AV_PATTERN.search(url):
            return url
        
        # If it's a short link, follow the redirect
        short_match = URLValidator.SHORT_LINK_PATTERN.search(url)
        if short_match:
            # Ensure the URL has a scheme
            if not url.startswith('http'):
                url = 'https://' + url
            
            try:
                # Follow redirects to get the final URL
                response = requests.head(url, allow_redirects=True, timeout=10)
                final_url = response.url
                
                # Verify the final URL is a valid Bilibili video URL
                if URLValidator.BV_PATTERN.search(final_url) or URLValidator.AV_PATTERN.search(final_url):
                    return final_url
                else:
                    raise URLValidationError(
                        f"Short link did not redirect to a valid Bilibili video URL: {final_url}"
                    )
            except requests.RequestException as e:
                raise URLValidationError(f"Failed to resolve short link: {str(e)}")
        
        raise URLValidationError(
            f"Invalid Bilibili URL format. Supported formats: "
            f"bilibili.com/video/BV*, bilibili.com/video/av*, b23.tv/*"
        )

    @staticmethod
    def extract_page_number(url: str) -> int:
        """Extract page number from URL.

        For multi-page videos, the URL may contain a 'p' parameter (e.g., ?p=2).
        If no page parameter is found, returns 1 (first page).

        Args:
            url: Bilibili video URL

        Returns:
            Page number (1-indexed)
        """
        if not url or not isinstance(url, str):
            return 1

        # Extract p parameter from URL
        # Examples:
        # - https://www.bilibili.com/video/BV1xx411c7mD?p=2
        # - https://www.bilibili.com/video/BV1xx411c7mD/?p=2&other=value
        import re
        from urllib.parse import urlparse, parse_qs

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # Get 'p' parameter
            if 'p' in query_params:
                page_str = query_params['p'][0]
                page_num = int(page_str)
                return max(1, page_num)  # Ensure at least 1
        except (ValueError, IndexError, KeyError):
            pass

        return 1
