"""Command-line interface that prints or writes JSON Lines."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TextIO

from .collector import PlaywrightCollectorConfig
from .service import collect_proxies


def _open_output(path: str | None) -> nullcontext[TextIO] | TextIO:
    if path is None:
        return nullcontext(sys.stdout)
    return Path(path).open("w", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect free proxy IPs")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--captcha-retries", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--proxy", help="browser proxy, for example http://ip:port")
    parser.add_argument("--min-delay", type=float, default=0.5, help="minimum delay seconds")
    parser.add_argument("--max-delay", type=float, default=1.5, help="maximum delay seconds")
    parser.add_argument("--output", help="JSONL path; defaults to stdout")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    config = PlaywrightCollectorConfig(
        max_pages=args.max_pages,
        captcha_retries=args.captcha_retries,
        timeout_ms=int(args.timeout * 1000),
        headless=not args.headed,
        proxy_server=args.proxy,
        min_delay_ms=max(0, int(args.min_delay * 1000)),
        max_delay_ms=max(0, int(args.max_delay * 1000)),
    )
    records = collect_proxies(config)
    with _open_output(args.output) as stream:
        for record in records:
            stream.write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")
    logging.info("Collected %s unique proxies", len(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
