"""httpmini — minimal vendored HTTP client.

Capabilities: per-request timeout, custom headers. Nothing else.
(No retry logic, no jitter, no connection pooling, no async.)
"""

import json
import urllib.request


class HttpMini:
    """Tiny wrapper over urllib. One request, one connection."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, headers: dict | None = None) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}",
            headers=headers or {},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def post(self, path: str, body: dict, headers: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8")
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=data,
            headers=hdrs,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
