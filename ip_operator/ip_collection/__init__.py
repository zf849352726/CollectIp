"""Standalone Playwright proxy collection package."""

from .captcha import DdddOcrCaptchaSolver
from .collector import (
    CollectionError,
    FreeProxyListCollector,
    PlaywrightCollectorConfig,
)
from .models import ProxyRecord
from .service import collect_proxies

__all__ = [
    "CollectionError",
    "DdddOcrCaptchaSolver",
    "FreeProxyListCollector",
    "PlaywrightCollectorConfig",
    "ProxyRecord",
    "collect_proxies",
]
