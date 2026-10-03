"""Playwright collector for freeproxylist.org."""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol
from urllib.parse import urljoin

from .captcha import DdddOcrCaptchaSolver
from .models import ProxyRecord

LOGGER = logging.getLogger(__name__)


class CaptchaSolver(Protocol):
    def solve(self, image: bytes) -> str: ...


class CollectionError(RuntimeError):
    pass


class CollectionBlockedError(CollectionError):
    pass


EventCallback = Callable[[str, str, str, dict[str, Any]], None]


@dataclass(frozen=True)
class PlaywrightCollectorConfig:
    source_url: str = "https://freeproxylist.org/en/free-proxy-list.htm"
    max_pages: int = 5
    captcha_retries: int = 5
    timeout_ms: int = 30_000
    headless: bool = True
    locale: str = "en-US"
    timezone_id: str = "UTC"
    user_agent: str | None = None
    proxy_server: str | None = None
    min_delay_ms: int = 500
    max_delay_ms: int = 1500
    max_runtime_seconds: int = 300

    def __post_init__(self) -> None:
        if self.max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if self.captcha_retries < 1:
            raise ValueError("captcha_retries must be at least 1")
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be positive")
        if self.min_delay_ms < 0 or self.max_delay_ms < self.min_delay_ms:
            raise ValueError("delay range is invalid")
        if self.max_runtime_seconds < 1:
            raise ValueError("max_runtime_seconds must be positive")


class FreeProxyListCollector:
    _TABLE_ROWS = "#proxytable tbody tr"
    _CAPTCHA_IMAGE = "#tbl_filter img"

    def __init__(
        self,
        config: Optional[PlaywrightCollectorConfig] = None,
        *,
        captcha_solver: Optional[CaptchaSolver] = None,
        logger: Optional[logging.Logger] = None,
        event_callback: EventCallback | None = None,
    ) -> None:
        self.config = config or PlaywrightCollectorConfig()
        self.captcha_solver = captcha_solver or DdddOcrCaptchaSolver()
        self.logger = logger or LOGGER
        self.event_callback = event_callback
        self._started_at = 0.0

    def _emit(
        self, level: str, event: str, message: str, **details: Any
    ) -> None:
        getattr(self.logger, level.lower(), self.logger.info)(message)
        if self.event_callback:
            self.event_callback(level.upper(), event, message, details)

    def _human_delay(self, page: Any) -> None:
        if self.config.max_delay_ms:
            page.wait_for_timeout(
                random.randint(self.config.min_delay_ms, self.config.max_delay_ms)
            )

    def _check_runtime(self) -> None:
        if time.monotonic() - self._started_at > self.config.max_runtime_seconds:
            raise CollectionError("Collection exceeded its maximum runtime")

    @staticmethod
    def _browser_user_agent(browser: Any) -> str:
        version = browser.version
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{version} Safari/537.36"
        )

    def collect(self) -> list[ProxyRecord]:
        project_browsers = Path(__file__).resolve().parents[2] / ".playwright-browsers"
        if project_browsers.is_dir():
            os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(project_browsers))
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Install requirements and run "
                "`playwright install chromium`."
            ) from exc

        records: dict[str, ProxyRecord] = {}
        self._started_at = time.monotonic()
        with sync_playwright() as playwright:
            launch_options: dict[str, Any] = {
                "headless": self.config.headless,
                "args": ["--disable-dev-shm-usage", "--no-sandbox"],
            }
            if self.config.proxy_server:
                launch_options["proxy"] = {"server": self.config.proxy_server}
            browser = playwright.chromium.launch(
                **launch_options,
            )
            try:
                viewport = random.choice(
                    ((1366, 768), (1440, 900), (1536, 864), (1920, 1080))
                )
                user_agent = self.config.user_agent or self._browser_user_agent(browser)
                context = browser.new_context(
                    locale=self.config.locale,
                    timezone_id=self.config.timezone_id,
                    user_agent=user_agent,
                    viewport={"width": viewport[0], "height": viewport[1]},
                    extra_http_headers={
                        "Accept-Language": f"{self.config.locale},en;q=0.8",
                        "DNT": "1",
                    },
                )
                page = context.new_page()
                page.set_default_timeout(self.config.timeout_ms)
                self._emit(
                    "INFO",
                    "browser_started",
                    "Browser session started",
                    route="proxy" if self.config.proxy_server else "direct",
                    viewport=f"{viewport[0]}x{viewport[1]}",
                    user_agent=user_agent,
                )
                response = page.goto(
                    self.config.source_url,
                    wait_until="domcontentloaded",
                    timeout=self.config.timeout_ms,
                )
                if response and response.status in {403, 429}:
                    raise CollectionBlockedError(
                        f"Source returned HTTP {response.status}"
                    )
                self._human_delay(page)
                self._unlock_table(page)
                self._collect_pages(page, records)
            finally:
                browser.close()
        return list(records.values())

    def _select_free_proxies(self, page: Any) -> None:
        selector = page.locator("#select9")
        selector.wait_for(state="visible")
        selector.select_option(label="free proxy servers")

    def _unlock_table(self, page: Any) -> None:
        for attempt in range(1, self.config.captcha_retries + 1):
            self._check_runtime()
            self._select_free_proxies(page)
            image = page.locator(self._CAPTCHA_IMAGE)
            image.wait_for(state="visible")
            answer = self.captcha_solver.solve(self._captcha_bytes(page, image))
            if answer:
                page.locator("#code").fill(answer)
                page.locator("#filter").click()
                page.locator("#proxytable").wait_for(state="visible")
                if self._wait_for_unlocked_table(page):
                    self._emit(
                        "INFO",
                        "captcha_accepted",
                        f"Captcha accepted on attempt {attempt}",
                        attempt=attempt,
                    )
                    return
            self._emit(
                "WARNING",
                "captcha_failed",
                f"Captcha failed on attempt {attempt}",
                attempt=attempt,
            )
            if attempt < self.config.captcha_retries:
                self._human_delay(page)
                page.reload(
                    wait_until="domcontentloaded", timeout=self.config.timeout_ms
                )
        raise CollectionError(
            f"Captcha was not accepted after {self.config.captcha_retries} attempts"
        )

    @staticmethod
    def _captcha_bytes(page: Any, image: Any) -> bytes:
        """Download the captcha with the browser context's current cookies.

        Element screenshots of this site's image can be a blank rectangle in
        headless Chromium even though the underlying JPEG is valid.
        """
        source = image.get_attribute("src")
        if not source:
            raise CollectionError("Captcha image has no source URL")
        response = page.request.get(urljoin(page.url, source))
        if not response.ok:
            raise CollectionError(
                f"Captcha image request failed with HTTP {response.status}"
            )
        content = response.body()
        if not content:
            raise CollectionError("Captcha image response was empty")
        return content

    def _wait_for_unlocked_table(self, page: Any) -> bool:
        try:
            page.wait_for_function(
                """() => {
                    const cell = document.querySelector(
                        '#proxytable tbody tr:nth-child(2) td:nth-child(2)'
                    );
                    const server = cell?.textContent.trim() || '';
                    return server.length > 0 && !server.includes('*');
                }""",
                timeout=self.config.timeout_ms,
            )
            return True
        except Exception:
            return False

    def _collect_pages(self, page: Any, records: dict[str, ProxyRecord]) -> None:
        for page_number in range(1, self.config.max_pages + 1):
            self._check_runtime()
            raw_rows = page.locator(self._TABLE_ROWS).evaluate_all(
                self._extract_rows_script()
            )
            for raw in raw_rows:
                try:
                    record = ProxyRecord.from_mapping(raw)
                except ValueError:
                    continue
                records[record.server] = record
            self._emit(
                "INFO",
                "page_collected",
                f"Collected page {page_number} ({len(records)} unique proxies)",
                page=page_number,
                unique_proxies=len(records),
            )
            if page_number == self.config.max_pages or not self._go_to_page(
                page, page_number + 1
            ):
                break

    def _go_to_page(self, page: Any, target: int) -> bool:
        links = page.locator("#container table tbody tr:nth-child(4) a")
        matches = links.filter(has_text=str(target))
        for index in range(matches.count()):
            candidate = matches.nth(index)
            if candidate.inner_text().strip() != str(target):
                continue
            previous = self._first_server(page)
            self._human_delay(page)
            candidate.click()
            page.wait_for_timeout(500)
            try:
                page.wait_for_function(
                    """previous => {
                        const cell = document.querySelector(
                            '#proxytable tbody tr:nth-child(2) td:nth-child(2)'
                        );
                        return cell && cell.textContent.trim() !== previous;
                    }""",
                    previous,
                    timeout=self.config.timeout_ms,
                )
            except Exception:
                page.locator("#proxytable").wait_for(state="visible")
            return True
        return False

    def _first_server(self, page: Any) -> str:
        rows = page.locator(self._TABLE_ROWS)
        if rows.count() < 2:
            return ""
        cells = rows.nth(1).locator("td")
        return cells.nth(1).inner_text().strip() if cells.count() > 1 else ""

    @staticmethod
    def _extract_rows_script() -> str:
        return """
        rows => rows.slice(1).map(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            const text = index => (cells[index]?.textContent || '').trim();
            const title = (index, selector) =>
                cells[index]?.querySelector(selector)?.getAttribute('title') || 'N/A';
            return {
                server: text(1), ping: text(2), speed: text(3),
                uptime1: text(4), uptime2: text(5), type_data: text(6),
                country: text(7), ssl: title(8, 'img'), conn: title(9, 'img'),
                post: title(10, 'img'), last_work_time: title(11, 'div')
            };
        }).filter(row => row.server && !row.server.includes('*'))
        """
