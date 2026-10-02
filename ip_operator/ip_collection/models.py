"""Normalized proxy data returned by the collector."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "?":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _text(value: Any, default: str = "N/A") -> str:
    text = "" if value is None else str(value).strip()
    return text or default


@dataclass(frozen=True)
class ProxyRecord:
    server: str
    ping: Optional[float] = None
    speed: Optional[float] = None
    uptime1: str = "N/A"
    uptime2: str = "N/A"
    type_data: str = "Unknown"
    country: str = "Unknown"
    ssl: str = "N/A"
    conn: str = "N/A"
    post: str = "N/A"
    last_work_time: str = "N/A"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProxyRecord":
        server = _text(data.get("server"), default="")
        if not server:
            raise ValueError("proxy server must not be empty")
        return cls(
            server=server,
            ping=_optional_float(data.get("ping")),
            speed=_optional_float(data.get("speed")),
            uptime1=_text(data.get("uptime1")),
            uptime2=_text(data.get("uptime2")),
            type_data=_text(data.get("type_data"), "Unknown"),
            country=_text(data.get("country"), "Unknown"),
            ssl=_text(data.get("ssl")),
            conn=_text(data.get("conn")),
            post=_text(data.get("post")),
            last_work_time=_text(data.get("last_work_time")),
        )

    @property
    def supports_https(self) -> bool:
        status = self.ssl.casefold()
        if any(
            marker in status
            for marker in ("does not", "not support", "unsupported", "不支持")
        ):
            return False
        return any(
            marker in status
            for marker in ("support", "yes", "true", "https", "支持")
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
