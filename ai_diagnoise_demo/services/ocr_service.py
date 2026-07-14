"""OCR abstraction for screenshot text extraction."""

from __future__ import annotations

from pathlib import Path


class OcrService:
    """Interface placeholder for PaddleOCR, RapidOCR or multimodal OCR."""

    def extract(self, _image_path: Path) -> dict[str, str]:
        return {
            "engine": "multimodal_llm",
            "text": "",
            "note": "Demo uses the vision model for OCR; replace with PaddleOCR/RapidOCR in production.",
        }
