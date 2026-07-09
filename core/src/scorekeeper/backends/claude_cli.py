"""Headless ``claude -p`` fallback backend (uses the user's subscription).

Slowest option (spawns the full CLI); last in the auto-detect order.
"""

from __future__ import annotations

import shutil
import subprocess

from .base import BackendError

DEFAULT_MODEL = "haiku"


class ClaudeCLIBackend:
    name = "claude_cli"

    def __init__(self, model: str = DEFAULT_MODEL, timeout: float = 120.0):
        self.model = model
        self.timeout = timeout

    @staticmethod
    def available() -> bool:
        return shutil.which("claude") is not None

    def complete(self, system: str, user: str) -> str:
        if not self.available():
            raise BackendError("claude CLI not found on PATH")
        prompt = f"{system}\n\n---\n\n{user}"
        try:
            proc = subprocess.run(
                ["claude", "-p", "--model", self.model, "--output-format", "text", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise BackendError(f"{self.name}: timed out after {self.timeout}s") from e
        if proc.returncode != 0:
            detail = (proc.stderr.strip() or proc.stdout.strip())[:500]
            raise BackendError(f"{self.name}: exit {proc.returncode}: {detail}")
        return proc.stdout
