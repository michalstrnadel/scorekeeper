"""ModelBackend protocol + shared JSON plumbing (ADR-0003).

Backends are dumb: they take (system, user), return the model's text, and
offer a shared helper to coerce that text into a JSON object. Validation
against a schema is the *caller's* job (write-path validation, SPEC §4.1.3);
retry-with-repair lives in the extractor, not here.
"""

from __future__ import annotations

import json
import re
from typing import Protocol, runtime_checkable


class BackendError(RuntimeError):
    """The backend call itself failed (network, auth, missing binary)."""


class JSONParseError(ValueError):
    """The model responded, but no JSON object could be recovered."""

    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw


@runtime_checkable
class ModelBackend(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str:
        """One isolated completion. Returns raw model text."""
        ...


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json_object(text: str) -> dict:
    """Recover a JSON object from model text (fences, leading prose tolerated)."""
    candidates = [m.strip() for m in _FENCE_RE.findall(text)]
    candidates.append(text.strip())
    # last resort: first {...} span
    brace_start = text.find("{")
    if brace_start != -1:
        candidates.append(text[brace_start : text.rfind("}") + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    raise JSONParseError("no JSON object found in model output", raw=text)


def complete_json(backend: ModelBackend, system: str, user: str) -> dict:
    """complete() + parse. Raises JSONParseError with the raw text attached."""
    return parse_json_object(backend.complete(system, user))
