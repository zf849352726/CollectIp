from __future__ import annotations

import ipaddress
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

from .models import Proxy, ProxyCheckHistory, SystemSettings


@dataclass(frozen=True)
class CheckAttempt:
    available: bool
    test_url: str
    protocol: str
    latency_ms: int | None = None
    exit_ip: str | None = None
    error_type: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class CheckResult:
    available: bool
    score: int
    latency_ms: int | None
    attempts: tuple[CheckAttempt, ...]


def _extract_public_ip(response: requests.Response) -> str | None:
    candidates: list[str] = []
    try:
        data = response.json()
        if isinstance(data, dict):
            for key in ("ip", "origin", "query"):
                if data.get(key):
                    candidates.extend(str(data[key]).replace(",", " ").split())
    except (ValueError, json.JSONDecodeError):
        candidates.extend(response.text.strip().replace(",", " ").split())
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_global:
            return str(address)
    return None


class ProxyScorer:
    def __init__(
        self,
        test_urls: list[str] | None = None,
        timeout: int | None = None,
    ) -> None:
        self.test_urls = test_urls or list(settings.PROXY_CHECK_URLS)
        self.timeout = timeout or settings.PROXY_CHECK_TIMEOUT

    def check(self, server: str, previous_failures: int = 0) -> CheckResult:
        proxy_url = f"http://{server}"
        attempts: list[CheckAttempt] = []
        for url in self.test_urls:
            protocol = urlparse(url).scheme.lower()
            started = time.perf_counter()
            try:
                response = requests.get(
                    url,
                    proxies={"http": proxy_url, "https": proxy_url},
                    timeout=self.timeout,
                    headers={"User-Agent": "CollectIP/2.2"},
                )
                response.raise_for_status()
                latency = max(1, round((time.perf_counter() - started) * 1000))
                exit_ip = _extract_public_ip(response)
                if not exit_ip:
                    raise ValueError("response did not contain a public exit IP")
                attempts.append(
                    CheckAttempt(True, url, protocol, latency, exit_ip=exit_ip)
                )
            except (requests.RequestException, ValueError) as exc:
                attempts.append(
                    CheckAttempt(
                        False,
                        url,
                        protocol,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:255],
                    )
                )

        successful = [attempt for attempt in attempts if attempt.available]
        if not successful:
            return CheckResult(False, 0, None, tuple(attempts))
        average_latency = round(
            sum(attempt.latency_ms or 0 for attempt in successful) / len(successful)
        )
        current_success_rate = len(successful) / len(attempts)
        latency_score = max(0, 30 - average_latency // 150)
        stability_score = max(0, 20 - previous_failures * 4)
        score = round(current_success_rate * 50 + latency_score + stability_score)
        return CheckResult(True, min(100, score), average_latency, tuple(attempts))


def _rolling_metrics(proxy: Proxy, since) -> tuple[float, int | None]:
    aggregate = proxy.checks.filter(checked_at__gte=since).aggregate(
        total=Count("id"),
        successes=Count("id", filter=Q(available=True)),
        average_latency=Avg("latency_ms", filter=Q(available=True)),
    )
    total = aggregate["total"] or 0
    success_rate = (aggregate["successes"] or 0) / total * 100 if total else 0
    average = aggregate["average_latency"]
    return round(success_rate, 2), round(average) if average is not None else None


def score_all_proxies(progress_callback=None) -> dict[str, int]:
    pool = list(Proxy.objects.filter(is_archived=False))
    if not pool:
        return {"checked": 0, "available": 0, "unavailable": 0, "archived": 0}

    config = SystemSettings.load()
    scorer = ProxyScorer(timeout=config.check_timeout)
    workers = min(config.check_workers, len(pool))
    results: dict[int, CheckResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scorer.check, proxy.server, proxy.consecutive_failures): proxy.pk
            for proxy in pool
        }
        completed = 0
        for future in as_completed(futures):
            proxy_id = futures[future]
            try:
                results[proxy_id] = future.result()
            except Exception as exc:
                attempt = CheckAttempt(
                    False,
                    settings.PROXY_CHECK_URLS[0],
                    "https",
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:255],
                )
                results[proxy_id] = CheckResult(False, 0, None, (attempt,))
            completed += 1
            if progress_callback:
                progress_callback(completed, len(pool))

    now = timezone.now()
    history_rows: list[ProxyCheckHistory] = []
    for proxy in pool:
        for attempt in results[proxy.pk].attempts:
            history_rows.append(
                ProxyCheckHistory(
                    proxy=proxy,
                    available=attempt.available,
                    latency_ms=attempt.latency_ms,
                    error_type=attempt.error_type,
                    error_message=attempt.error_message,
                    exit_ip=attempt.exit_ip,
                    test_url=attempt.test_url,
                    protocol=attempt.protocol,
                )
            )
    ProxyCheckHistory.objects.bulk_create(history_rows)

    available = 0
    archived = 0
    since = now - timedelta(hours=24)
    for proxy in pool:
        result = results[proxy.pk]
        proxy.is_available = result.available
        proxy.last_checked_at = now
        proxy.last_error = next(
            (attempt.error_message for attempt in result.attempts if not attempt.available),
            "",
        )
        if result.available:
            proxy.score = result.score
            proxy.latency_ms = result.latency_ms
            proxy.consecutive_failures = 0
            proxy.last_success_at = now
            available += 1
        else:
            proxy.latency_ms = None
            proxy.score = max(0, proxy.score - 10)
            proxy.consecutive_failures += 1
            if proxy.consecutive_failures >= config.archive_after_failures:
                proxy.is_archived = True
                proxy.archived_at = now
                archived += 1
        proxy.success_rate, rolling_latency = _rolling_metrics(proxy, since)
        if result.available and rolling_latency is not None:
            proxy.latency_ms = rolling_latency
        proxy.save()

    config.last_score_at = now
    config.save(update_fields=["last_score_at"])
    return {
        "checked": len(pool),
        "available": available,
        "unavailable": len(pool) - available,
        "archived": archived,
    }
