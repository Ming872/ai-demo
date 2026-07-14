"""Backward-compatible wrapper around the unified model gateway."""

from __future__ import annotations

from pathlib import Path

from services.model_gateway import ModelGateway, ModelGatewayError, encode_image

_gateway: ModelGateway | None = None


class ClaudeClientError(RuntimeError):
    """Raised when legacy Claude calls fail."""


def _get_gateway() -> ModelGateway:
    global _gateway
    if _gateway is None:
        _gateway = ModelGateway()
    return _gateway


def analyze_image(image_path: str | Path, prompt_text: str, media_type: str = "image/png") -> str:
    try:
        return _get_gateway().analyze_image(image_path, prompt_text, media_type)
    except ModelGatewayError as exc:
        raise ClaudeClientError(str(exc)) from exc
