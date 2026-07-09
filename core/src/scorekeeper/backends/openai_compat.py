"""OpenAI-compatible backend — the local open-source path (ADR-0003).

One client covers Ollama, LM Studio, and vLLM: all serve
``POST <base_url>/chat/completions``. stdlib-only (urllib), no extra deps.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from .base import BackendError

DEFAULT_MODEL = "qwen3:8b"

_RETRY_IN_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)
MAX_429_RETRIES = 3


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
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(MAX_429_RETRIES + 1):
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:800]
                if e.code == 429 and attempt < MAX_429_RETRIES:
                    time.sleep(self._retry_delay(e, detail))
                    continue
                raise BackendError(f"{self.name}: HTTP {e.code}: {detail[:500]}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                raise BackendError(f"{self.name}: {e}") from e
        raise BackendError(f"{self.name}: unreachable")  # pragma: no cover

    @staticmethod
    def _retry_delay(err: urllib.error.HTTPError, detail: str) -> float:
        """Honor Retry-After / 'retry in Xs' hints; cap at 65s (per-minute windows)."""
        header = err.headers.get("Retry-After") if err.headers else None
        if header and header.replace(".", "", 1).isdigit():
            return min(float(header) + 1.0, 65.0)
        match = _RETRY_IN_RE.search(detail)
        if match:
            return min(float(match.group(1)) + 1.0, 65.0)
        return 30.0

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
