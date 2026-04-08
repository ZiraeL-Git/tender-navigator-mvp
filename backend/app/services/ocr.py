from __future__ import annotations


class OcrService:
    def run_fallback(self, file_records: list[dict]) -> dict | None:
        # OCR provider is not connected yet. The hook lives here so that the
        # background pipeline already has a stable extension point.
        return None
