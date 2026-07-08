"""OpenAI-compatible backend — the local open-source path (ADR-0003).

One client covers Ollama, LM Studio, and vLLM: all serve
``POST <base_url>/chat/completions``. stdlib-only (urllib), no extra deps.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import BackendError

DEFAULT_MODEL = "qwen3:8b"


class OpenAICompatBackend:
    name = "openai_compat"

    def __init__(
        self,
        base_url: str,
        model: str = DEFAULT_MODEL,
        api_key: str = "",
        timeout: float = 120.0,
        temperature: float = 0.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature

    def _post(self, payload: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise BackendError(f"{self.name}: HTTP {e.code}: {e.read().decode()[:500]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise BackendError(f"{self.name}: {e}") from e

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            data = self._post(payload)
        except BackendError:
            # some servers reject response_format — retry once without it
            payload.pop("response_format")
            data = self._post(payload)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise BackendError(f"{self.name}: malformed response: {data}") from e
