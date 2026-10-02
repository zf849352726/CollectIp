"""Captcha recognition used by the source website."""

from __future__ import annotations


class DdddOcrCaptchaSolver:
    def __init__(self) -> None:
        self._engine = None

    def solve(self, image: bytes) -> str:
        if self._engine is None:
            try:
                from ddddocr import DdddOcr
            except ImportError as exc:
                raise RuntimeError("ddddocr is required for captcha recognition") from exc
            self._engine = DdddOcr(show_ad=False)
        return str(self._engine.classification(image)).strip()
