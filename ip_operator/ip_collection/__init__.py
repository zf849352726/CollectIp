"""Standalone Playwright proxy collection package."""

from .captcha import DdddOcrCaptchaSolver
from .collector import (
    CollectionError,
    CollectionBlockedError,
    FreeProxyListCollector,
    PlaywrightCollectorConfig,
)
from .models import ProxyRecord
from .service import collect_proxies

__all__ = [
    "CollectionError",
    "CollectionBlockedError",
    "DdddOcrCaptchaSolver",
    "FreeProxyListCollector",
    "PlaywrightCollectorConfig",
    "ProxyRecord",
    "collect_proxies",
]
