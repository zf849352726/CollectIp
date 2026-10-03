"""Small stable API for collecting proxies."""

from __future__ import annotations

from typing import Optional

from .collector import EventCallback, FreeProxyListCollector, PlaywrightCollectorConfig
from .models import ProxyRecord


def collect_proxies(
    config: Optional[PlaywrightCollectorConfig] = None,
    *,
    event_callback: EventCallback | None = None,
) -> list[ProxyRecord]:
    return FreeProxyListCollector(
        config=config, event_callback=event_callback
    ).collect()
