"""Auto-tracing module for HTTP libraries.

This module provides convenient functions to automatically trace all HTTP requests
from various HTTP libraries without requiring manual patching of individual instances.
"""

from contextlib import suppress

from async_trace import disable_tracing, enable_tracing

from r4u.client import AbstractTracer, get_r4u_client
from r4u.tracing.http.filters import URLFilter, get_global_filter, set_global_filter


def trace_all_http(
    tracer: AbstractTracer | None = None,
    allow_urls: list[str] | None = None,
    deny_urls: list[str] | None = None,
) -> None:
    """Enable automatic tracing for all supported HTTP libraries.

    This function monkey patches all supported HTTP libraries to automatically
    trace all HTTP requests made through them.

    Args:
        tracer: Optional tracer instance. If None, uses the default R4U client.
        allow_urls: Optional list of URL patterns to allow. If provided, extends default AI provider patterns.
        deny_urls: Optional list of URL patterns to deny. Takes precedence over allow patterns.

    Example:
        >>> from r4u.tracing.http.auto import trace_all_http
        >>> trace_all_http()  # Enable tracing for all HTTP libraries with default patterns
        >>>
        >>> # Or with custom patterns
        >>> trace_all_http(
        ...     allow_urls=["https://api.custom.com/*"],
        ...     deny_urls=["https://api.openai.com/v1/models"]
        ... )
        >>>
        >>> # Now all HTTP requests will be automatically traced
        >>> import httpx
        >>> import requests
        >>> import aiohttp
        >>>
        >>> # All of these will be automatically traced
        >>> httpx_client = httpx.Client()
        >>> requests_session = requests.Session()
        >>> aiohttp_session = aiohttp.ClientSession()

    """
    enable_tracing()
    tracer = tracer or get_r4u_client()

    # Configure URL filter if patterns are provided
    if allow_urls is not None or deny_urls is not None:
        configure_url_filter(
            allow_urls=allow_urls,
            deny_urls=deny_urls,
            extend_defaults=True,  # Always extend defaults when called from trace_all_http
        )

    with suppress(Exception):
        from .httpx import trace_all as trace_httpx_all
        trace_httpx_all(tracer)

    with suppress(Exception):
        from .requests import trace_all as trace_requests_all
        trace_requests_all(tracer)

    with suppress(Exception):
        from .aiohttp import trace_all as trace_aiohttp_all
        trace_aiohttp_all(tracer)


def untrace_all_http() -> None:
    """Disable automatic tracing for all supported HTTP libraries.

    This function removes monkey patching from all supported HTTP libraries,
    restoring their original behavior.
    """
    disable_tracing()
    with suppress(Exception):
        from .httpx import untrace_all as untrace_httpx_all
        untrace_httpx_all()

    with suppress(Exception):
        from .requests import untrace_all as untrace_requests_all
        untrace_requests_all()

    with suppress(Exception):
        from .aiohttp import untrace_all as untrace_aiohttp_all
        untrace_aiohttp_all()


def configure_url_filter(
    allow_urls: list[str] | None = None,
    deny_urls: list[str] | None = None,
    extend_defaults: bool = True,
) -> None:
    """Configure the global URL filter for HTTP tracing.

    Args:
        allow_urls: List of URL patterns to allow. If None, uses default AI provider patterns.
        deny_urls: List of URL patterns to deny. Takes precedence over allow patterns.
        extend_defaults: If True and allow_urls is provided, extends default patterns instead of replacing them.

    Example:
        >>> from r4u.tracing.http.auto import configure_url_filter
        >>> configure_url_filter(
        ...     allow_urls=["https://api.openai.com/*", "https://api.anthropic.com/*"],
        ...     deny_urls=["https://api.openai.com/v1/models"]
        ... )

    """
    # If extending defaults and we have an existing filter, extend from it
    if extend_defaults and (allow_urls is not None or deny_urls is not None):
        try:
            current_filter = get_global_filter()
            # Extend existing allow patterns
            if allow_urls is not None:
                current_allow = current_filter.get_allow_urls()
                new_allow = current_allow + allow_urls
            else:
                new_allow = current_filter.get_allow_urls()

            # Extend existing deny patterns
            if deny_urls is not None:
                current_deny = current_filter.get_deny_urls()
                new_deny = current_deny + deny_urls
            else:
                new_deny = current_filter.get_deny_urls()

            filter_instance = URLFilter(
                allow_urls=new_allow,
                deny_urls=new_deny,
                extend_defaults=False,  # Don't extend again since we already did
            )
        except Exception:
            # If no existing filter or error, create new one
            filter_instance = URLFilter(
                allow_urls=allow_urls,
                deny_urls=deny_urls,
                extend_defaults=extend_defaults,
            )
    else:
        filter_instance = URLFilter(
            allow_urls=allow_urls,
            deny_urls=deny_urls,
            extend_defaults=extend_defaults,
        )

    set_global_filter(filter_instance)


def get_url_filter() -> URLFilter:
    """Get the current global URL filter.

    Returns:
        The current global URL filter instance

    """
    return get_global_filter()


# Convenience aliases
trace_all = trace_all_http
untrace_all = untrace_all_http
