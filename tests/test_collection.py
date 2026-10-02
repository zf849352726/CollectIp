from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ip_operator.ip_collection import PlaywrightCollectorConfig, ProxyRecord
from ip_operator.ip_collection.__main__ import main


class ProxyRecordTests(unittest.TestCase):
    def test_normalizes_values(self):
        record = ProxyRecord.from_mapping(
            {
                "server": " 127.0.0.1:8080 ",
                "ping": "0.42",
                "speed": "?",
                "country": "",
                "ssl": "proxy supports SSL/HTTPS",
            }
        )
        self.assertEqual(record.server, "127.0.0.1:8080")
        self.assertEqual(record.ping, 0.42)
        self.assertIsNone(record.speed)
        self.assertEqual(record.country, "Unknown")
        self.assertTrue(record.supports_https)

    def test_rejects_empty_server(self):
        with self.assertRaises(ValueError):
            ProxyRecord.from_mapping({"server": " "})

    def test_detects_negative_https_status(self):
        record = ProxyRecord(
            server="127.0.0.1:8080", ssl="proxy does not support SSL/HTTPS"
        )
        self.assertFalse(record.supports_https)


class ConfigurationTests(unittest.TestCase):
    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            PlaywrightCollectorConfig(max_pages=0)
        with self.assertRaises(ValueError):
            PlaywrightCollectorConfig(captcha_retries=0)
        with self.assertRaises(ValueError):
            PlaywrightCollectorConfig(timeout_ms=0)


class CommandLineTests(unittest.TestCase):
    def test_writes_json_lines(self):
        record = ProxyRecord(server="127.0.0.1:8080", country="China")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proxies.jsonl"
            argv = ["collectip", "--max-pages", "1", "--output", str(output)]
            with patch("sys.argv", argv), patch(
                "ip_operator.ip_collection.__main__.collect_proxies",
                return_value=[record],
            ):
                self.assertEqual(main(), 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["server"], record.server)
            self.assertEqual(data["country"], "China")

    def test_writes_to_stdout_by_default(self):
        record = ProxyRecord(server="127.0.0.1:8080")
        stdout = io.StringIO()
        with patch("sys.argv", ["collectip", "--max-pages", "1"]), patch(
            "ip_operator.ip_collection.__main__.collect_proxies",
            return_value=[record],
        ), patch("sys.stdout", stdout):
            self.assertEqual(main(), 0)
        self.assertEqual(json.loads(stdout.getvalue())["server"], record.server)


if __name__ == "__main__":
    unittest.main()
