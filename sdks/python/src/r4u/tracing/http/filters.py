"""URL filtering module for HTTP tracing.

This module provides functionality to filter HTTP requests based on allow and deny patterns.
It supports wildcard patterns and provides default patterns for common AI providers.
"""

import fnmatch
from urllib.parse import urlparse


class URLFilter:
    """Filter HTTP requests based on allow and deny patterns."""

    def __init__(
        self,
        allow_urls: list[str] | None = None,
        deny_urls: list[str] | None = None,
        extend_defaults: bool = True,
    ):
        """Initialize the URL filter.
        
        Args:
            allow_urls: List of URL patterns to allow. If None, uses default AI provider patterns.
            deny_urls: List of URL patterns to deny. Takes precedence over allow patterns.
            extend_defaults: If True and allow_urls is provided, extends default patterns instead of replacing them.

        """
        if allow_urls is None:
            self.allow_patterns = self._get_default_allow_patterns()
        elif extend_defaults:
            # Extend default patterns with provided patterns
            default_patterns = self._get_default_allow_patterns()
            self.allow_patterns = default_patterns + allow_urls
        else:
            # Replace default patterns with provided patterns
            self.allow_patterns = allow_urls

        self.deny_patterns = deny_urls or []

        # Convert to sets for faster lookup
        self._allow_set = set(self.allow_patterns)
        self._deny_set = set(self.deny_patterns)

    def _get_default_allow_patterns(self) -> list[str]:
        """Get default allow patterns for common AI providers."""
        return [
            # OpenAI
            "https://api.openai.com/*",

            # Anthropic (Claude)
            "https://api.anthropic.com/*",

            # Groq
            "https://api.groq.com/*",

            # xAI (Grok)
            "https://api.x.ai/*",

            # Mistral AI
            "https://api.mistral.ai/*",

            # Google
            "https://generativelanguage.googleapis.com/*",
            "https://aiplatform.googleapis.com/*",
        ]

    def should_trace(self, url: str) -> bool:
        """Determine if a URL should be traced.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL should be traced, False otherwise

        """
        # First check deny patterns (they take precedence)
        if self._matches_any_pattern(url, self._deny_set):
            return False

        # Then check allow patterns
        if self._matches_any_pattern(url, self._allow_set):
            return True

        # If no patterns match, default to not tracing
        return False

    def _matches_any_pattern(self, url: str, patterns: set[str]) -> bool:
        """Check if a URL matches any of the given patterns.
        
        Args:
            url: The URL to check
            patterns: Set of patterns to match against
            
        Returns:
            True if the URL matches any pattern, False otherwise

        """
        if not patterns:
            return False

        # Parse the URL to extract components
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path

        # Create different variations of the URL to match against
        url_variations = [
            url,  # Full URL
            f"{parsed.scheme}://{host}{path}",  # URL without query/fragment
            f"{parsed.scheme}://{host}/*",  # Host with wildcard path
            host,  # Just the host
            f"{host}/*",  # Host with wildcard path
        ]

        # Check each pattern against each URL variation
        for pattern in patterns:
            for variation in url_variations:
                if fnmatch.fnmatch(variation.lower(), pattern.lower()):
                    return True

        return False

    def get_allow_urls(self) -> list[str]:
        """Get a copy of the allow URL patterns.
        
        Returns:
            List of allow URL patterns

        """
        return self.allow_patterns.copy()

    def get_deny_urls(self) -> list[str]:
        """Get a copy of the deny URL patterns.
        
        Returns:
            List of deny URL patterns

        """
        return self.deny_patterns.copy()


# Global filter instance
_global_filter: URLFilter | None = None


def get_global_filter() -> URLFilter:
    """Get the global URL filter instance.
    
    Returns:
        The global URL filter instance

    """
    global _global_filter
    if _global_filter is None:
        _global_filter = URLFilter()
    return _global_filter


def set_global_filter(filter_instance: URLFilter) -> None:
    """Set the global URL filter instance.
    
    Args:
        filter_instance: The filter instance to set as global

    """
    global _global_filter
    _global_filter = filter_instance


def should_trace_url(url: str) -> bool:
    """Check if a URL should be traced using the global filter.
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL should be traced, False otherwise

    """
    return get_global_filter().should_trace(url)
