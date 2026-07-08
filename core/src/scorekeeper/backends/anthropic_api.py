"""Anthropic API backend (Haiku-class default). Optional extra: scorekeeper[anthropic]."""

from __future__ import annotations

from .base import BackendError

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AnthropicBackend:
    name = "anthropic_api"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        max_tokens: int = 2048,
        timeout: float = 60.0,
    ):
        try:
            import anthropic
        except ImportError as e:
            raise BackendError(
                "anthropic package not installed — pip install 'scorekeeper[anthropic]'"
            ) from e
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self._errors = anthropic.APIError
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        try:
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except self._errors as e:
            raise BackendError(f"{self.name}: {e}") from e
        return "".join(block.text for block in msg.content if block.type == "text")
