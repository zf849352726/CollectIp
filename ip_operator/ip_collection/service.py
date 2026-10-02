"""Small stable API for collecting proxies."""

from __future__ import annotations

from typing import Optional

from .collector import FreeProxyListCollector, PlaywrightCollectorConfig
from .models import ProxyRecord


def collect_proxies(
    config: Optional[PlaywrightCollectorConfig] = None,
) -> list[ProxyRecord]:
    return FreeProxyListCollector(config=config).collect()
