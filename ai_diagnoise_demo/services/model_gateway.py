"""DeepSeek-based model gateway for multimodal diagnosis models."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MAX_TOKENS = 1400


class ModelGatewayError(RuntimeError):
    """Raised when the model gateway is misconfigured or a model call fails."""


class ModelGateway:
    """Route image analysis to DeepSeek via the OpenAI-compatible API."""

    def __init__(self) -> None:
        self.provider = os.getenv("AI_PROVIDER", "deepseek").lower()
        self.model = os.getenv("MODEL_GATEWAY_MODEL") or "deepseek-chat"
        self.max_tokens = int(os.getenv("MODEL_GATEWAY_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))

    def analyze_image(self, image_path: str | Path, prompt_text: str, media_type: str = "image/png") -> str:
        if self.provider in {"deepseek", "openai", "openai_compatible", "gateway"}:
            return self._analyze_with_deepseek(image_path, prompt_text, media_type)
        raise ModelGatewayError(f"Unsupported AI_PROVIDER: {self.provider}")

    def _analyze_with_deepseek(self, image_path: str | Path, prompt_text: str, media_type: str) -> str:
        base_url = os.getenv("MODEL_GATEWAY_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        api_key = os.getenv("MODEL_GATEWAY_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ModelGatewayError("MODEL_GATEWAY_API_KEY or DEEPSEEK_API_KEY is missing.")

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
            raise ModelGatewayError(f"DeepSeek gateway error: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise ModelGatewayError("DeepSeek gateway returned no choices.")
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return "".join(block.get("text", "") for block in content if isinstance(block, dict))
        return str(content)


def encode_image(image_path: str | Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
