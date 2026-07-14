"""Unified model gateway for multimodal diagnosis models."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from anthropic import Anthropic, APIError
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MAX_TOKENS = 1400


class ModelGatewayError(RuntimeError):
    """Raised when the model gateway is misconfigured or a model call fails."""


class ModelGateway:
    """Route image analysis to Anthropic or an OpenAI-compatible gateway."""

    def __init__(self) -> None:
        self.provider = os.getenv("AI_PROVIDER", "anthropic").lower()
        self.model = os.getenv("MODEL_GATEWAY_MODEL") or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.max_tokens = int(os.getenv("MODEL_GATEWAY_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        self._anthropic_client: Anthropic | None = None

    def analyze_image(self, image_path: str | Path, prompt_text: str, media_type: str = "image/png") -> str:
        if self.provider in {"anthropic", "claude"}:
            return self._analyze_with_anthropic(image_path, prompt_text, media_type)
        if self.provider in {"openai", "openai_compatible", "gateway"}:
            return self._analyze_with_openai_compatible(image_path, prompt_text, media_type)
        raise ModelGatewayError(f"Unsupported AI_PROVIDER: {self.provider}")

    def _analyze_with_anthropic(self, image_path: str | Path, prompt_text: str, media_type: str) -> str:
        client = self._get_anthropic_client()
        image_data = encode_image(image_path)

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt_text},
                        ],
                    }
                ],
            )
        except APIError as exc:
            raise ModelGatewayError(f"Anthropic API error: {exc}") from exc

        return "".join(block.text for block in message.content if block.type == "text")

    def _analyze_with_openai_compatible(self, image_path: str | Path, prompt_text: str, media_type: str) -> str:
        base_url = os.getenv("MODEL_GATEWAY_BASE_URL", "").rstrip("/")
        api_key = os.getenv("MODEL_GATEWAY_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not base_url:
            raise ModelGatewayError("MODEL_GATEWAY_BASE_URL is missing for OpenAI-compatible provider.")
        if not api_key:
            raise ModelGatewayError("MODEL_GATEWAY_API_KEY or OPENAI_API_KEY is missing.")

        image_data_url = f"data:{media_type};base64,{encode_image(image_path)}"
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelGatewayError(f"Model gateway error: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise ModelGatewayError("Model gateway returned no choices.")
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return "".join(block.get("text", "") for block in content if isinstance(block, dict))
        return str(content)

    def _get_anthropic_client(self) -> Anthropic:
        if self._anthropic_client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ModelGatewayError("ANTHROPIC_API_KEY is missing. Add it to .env.")
            self._anthropic_client = Anthropic(api_key=api_key)
        return self._anthropic_client


def encode_image(image_path: str | Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
