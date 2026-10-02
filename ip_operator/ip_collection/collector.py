"""Playwright collector for freeproxylist.org."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol
from urllib.parse import urljoin

from .captcha import DdddOcrCaptchaSolver
from .models import ProxyRecord

LOGGER = logging.getLogger(__name__)


class CaptchaSolver(Protocol):
    def solve(self, image: bytes) -> str: ...


class CollectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlaywrightCollectorConfig:
    source_url: str = "https://freeproxylist.org/en/free-proxy-list.htm"
    max_pages: int = 5
    captcha_retries: int = 5
    timeout_ms: int = 30_000
    headless: bool = True
    locale: str = "en-US"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __post_init__(self) -> None:
        if self.max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if self.captcha_retries < 1:
            raise ValueError("captcha_retries must be at least 1")
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be positive")


class FreeProxyListCollector:
    _TABLE_ROWS = "#proxytable tbody tr"
    _CAPTCHA_IMAGE = "#tbl_filter img"

    def __init__(
        self,
        config: Optional[PlaywrightCollectorConfig] = None,
        *,
        captcha_solver: Optional[CaptchaSolver] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or PlaywrightCollectorConfig()
        self.captcha_solver = captcha_solver or DdddOcrCaptchaSolver()
        self.logger = logger or LOGGER

    def collect(self) -> list[ProxyRecord]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Install requirements and run "
                "`playwright install chromium`."
            ) from exc

        records: dict[str, ProxyRecord] = {}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self.config.headless,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            try:
                context = browser.new_context(
                    locale=self.config.locale,
                    user_agent=self.config.user_agent,
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()
                page.set_default_timeout(self.config.timeout_ms)
                page.goto(
                    self.config.source_url,
                    wait_until="domcontentloaded",
                    timeout=self.config.timeout_ms,
                )
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
            self._select_free_proxies(page)
            image = page.locator(self._CAPTCHA_IMAGE)
            image.wait_for(state="visible")
            answer = self.captcha_solver.solve(self._captcha_bytes(page, image))
            if answer:
                page.locator("#code").fill(answer)
                page.locator("#filter").click()
                page.locator("#proxytable").wait_for(state="visible")
                if self._wait_for_unlocked_table(page):
                    self.logger.info("Captcha accepted on attempt %s", attempt)
                    return
            self.logger.warning("Captcha failed on attempt %s", attempt)
            if attempt < self.config.captcha_retries:
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
            raw_rows = page.locator(self._TABLE_ROWS).evaluate_all(
                self._extract_rows_script()
            )
            for raw in raw_rows:
                try:
                    record = ProxyRecord.from_mapping(raw)
                except ValueError:
                    continue
                records[record.server] = record
            self.logger.info(
                "Collected page %s (%s unique proxies)", page_number, len(records)
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
