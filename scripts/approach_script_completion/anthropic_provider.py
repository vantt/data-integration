"""anthropic_provider.py — Anthropic API adapter (API key, không phụ thuộc OAuth cá nhân).

Dùng cho luồng tự động (nightly, phase 05) khi cần tách quota khỏi subscription
codex cá nhân của user. Tốn phí mỗi lần gọi — cần ANTHROPIC_API_KEY thật.
"""
from __future__ import annotations

import os

from .errors import ApproachScriptCompletionError

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"


class AnthropicCompletionProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ApproachScriptCompletionError(
                "Thiếu ANTHROPIC_API_KEY — set env var trước khi dùng --provider anthropic."
            )

    @property
    def model_label(self) -> str:
        return self.model

    def complete(self, prompt: str, timeout: int) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise ApproachScriptCompletionError(
                "Thiếu package 'anthropic' — pip install -r scripts/requirements.txt"
            ) from exc

        client = anthropic.Anthropic(api_key=self._api_key, timeout=timeout)
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise ApproachScriptCompletionError(f"Anthropic API error: {exc}") from exc

        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
