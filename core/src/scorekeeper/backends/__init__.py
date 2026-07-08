"""Backend auto-detection (ADR-0003).

Order: explicit config → SCOREKEEPER_MODEL_URL (local OSS via OpenAI-compat)
→ ANTHROPIC_API_KEY (Haiku) → claude CLI on PATH.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from .anthropic_api import DEFAULT_MODEL as ANTHROPIC_DEFAULT
from .anthropic_api import AnthropicBackend
from .base import BackendError, JSONParseError, ModelBackend, complete_json, parse_json_object
from .claude_cli import DEFAULT_MODEL as CLI_DEFAULT
from .claude_cli import ClaudeCLIBackend
from .openai_compat import DEFAULT_MODEL as LOCAL_DEFAULT
from .openai_compat import OpenAICompatBackend

__all__ = [
    "AnthropicBackend",
    "BackendError",
    "ClaudeCLIBackend",
    "JSONParseError",
    "ModelBackend",
    "OpenAICompatBackend",
    "complete_json",
    "detect_backend",
    "parse_json_object",
]


def _load_config(root: Path | None) -> dict:
    if root is None:
        return {}
    path = Path(root) / ".scorekeeper" / "config.yaml"
    if not path.exists():
        return {}
    return (yaml.safe_load(path.read_text()) or {}).get("backend", {})


def detect_backend(root: Path | str | None = None, env: dict | None = None) -> ModelBackend:
    """Pick the scorer backend. Explicit config wins; env auto-detect otherwise."""
    env = env if env is not None else dict(os.environ)
    cfg = _load_config(Path(root) if root else None)

    kind = cfg.get("kind")
    if kind == "openai_compat":
        return OpenAICompatBackend(
            base_url=cfg.get("url") or env.get("SCOREKEEPER_MODEL_URL", ""),
            model=cfg.get("model", LOCAL_DEFAULT),
            api_key=cfg.get("api_key", env.get("SCOREKEEPER_MODEL_API_KEY", "")),
        )
    if kind == "anthropic_api":
        return AnthropicBackend(model=cfg.get("model", ANTHROPIC_DEFAULT))
    if kind == "claude_cli":
        return ClaudeCLIBackend(model=cfg.get("model", CLI_DEFAULT))

    # auto-detect
    if url := env.get("SCOREKEEPER_MODEL_URL"):
        return OpenAICompatBackend(
            base_url=url,
            model=env.get("SCOREKEEPER_MODEL", LOCAL_DEFAULT),
            api_key=env.get("SCOREKEEPER_MODEL_API_KEY", ""),
        )
    if env.get("ANTHROPIC_API_KEY"):
        return AnthropicBackend()
    if ClaudeCLIBackend.available():
        return ClaudeCLIBackend()
    raise BackendError(
        "no model backend available — set SCOREKEEPER_MODEL_URL (local OSS), "
        "ANTHROPIC_API_KEY, or install the claude CLI"
    )
