"""Multi-turn tool-calling backends for the reference loop (ADR-0009).

ADR-0003's ModelBackend is single-shot (system, user) -> text; an agent loop
needs tool calls in and tool results back. The loop keeps a NEUTRAL history
and hands it to run_turn() whole; each adapter translates to its wire format.

Neutral history messages:
    {"role": "user", "content": str}
    {"role": "assistant", "content": str, "tool_calls": [ToolCall...]}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str,
     "is_error": bool}

Both adapters are stdlib-only (urllib), mirroring core's
backends/openai_compat.py retry discipline: 429/5xx and dropped connections
retry with backoff under a total time budget.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from scorekeeper.backends import BackendError

MAX_RETRIES = 4
TRANSIENT_CODES = {429, 500, 502, 503, 529}
REQUEST_TIMEOUT_S = 300.0
BUDGET_S = 540.0  # sits under the loop's 600s phase cap

# providers hide the authoritative wait in the body, not the header — Gemini's
# free tier says "Please retry in 51.29s" while sending no Retry-After (seen
# live 2026-07-22, first loop smoke). Same regex family as core's
# openai_compat backend.
_RETRY_IN_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    parse_error: str = ""  # raw text when the provider sent unparseable JSON args


@dataclass
class TurnResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "stop"  # "stop" | "tool_calls" | "length"


class _Pacer:
    """Client-side request pacing for rate-limited (free-tier) keys: waiting
    by construction beats bouncing off 429s, which some quotas count."""

    def __init__(self, rpm: float | None):
        self.interval = 60.0 / rpm if rpm else 0.0
        self._last: float | None = None

    def wait(self) -> None:
        if not self.interval:
            return
        if self._last is not None:
            due = self._last + self.interval - time.monotonic()
            if due > 0:
                time.sleep(due)
        self._last = time.monotonic()


def _post_json(url: str, headers: dict, payload: dict, name: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    deadline = time.monotonic() + BUDGET_S
    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:800]
            if e.code in TRANSIENT_CODES and attempt < MAX_RETRIES:
                delay = 15.0 * (attempt + 1)
                header = e.headers.get("Retry-After") if e.headers else None
                hint = _RETRY_IN_RE.search(detail)
                if header and header.replace(".", "", 1).isdigit():
                    delay = min(float(header) + 1.0, 90.0)
                elif hint:
                    delay = min(float(hint.group(1)) + 1.0, 90.0)
                if time.monotonic() + delay <= deadline:
                    time.sleep(delay)
                    continue
            raise BackendError(f"{name}: HTTP {e.code}: {detail[:500]}") from e
        except (
            http.client.RemoteDisconnected,
            ConnectionResetError,
            ConnectionRefusedError,
        ) as e:
            delay = 10.0 * (attempt + 1)
            if attempt < MAX_RETRIES and time.monotonic() + delay <= deadline:
                time.sleep(delay)
                continue
            raise BackendError(f"{name}: connection dropped: {e}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise BackendError(f"{name}: {e}") from e
    raise BackendError(f"{name}: unreachable")  # pragma: no cover


class OpenAICompatAgentBackend:
    """One adapter for every /chat/completions server with function calling:
    OpenAI, Gemini (OpenAI-compat endpoint), OpenRouter, Ollama, LM Studio,
    vLLM."""

    name = "openai_compat"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        temperature: float | None = 0.0,
        rpm: float | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self._pacer = _Pacer(rpm)

    # -- wire translation ---------------------------------------------------

    @staticmethod
    def _translate_tools(tools: list[dict]) -> list[dict]:
        return [{"type": "function", "function": t} for t in tools]

    @staticmethod
    def _translate_history(system: str, messages: list[dict]) -> list[dict]:
        wire: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "assistant":
                entry: dict = {"role": "assistant", "content": m.get("content") or None}
                calls = m.get("tool_calls") or []
                if calls:
                    entry["tool_calls"] = [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.name,
                                "arguments": json.dumps(c.arguments),
                            },
                        }
                        for c in calls
                    ]
                wire.append(entry)
            elif m["role"] == "tool":
                content = m["content"]
                if m.get("is_error"):
                    content = f"ERROR: {content}"
                wire.append(
                    {"role": "tool", "tool_call_id": m["tool_call_id"], "content": content}
                )
            else:
                wire.append({"role": "user", "content": m["content"]})
        return wire

    @staticmethod
    def _parse_calls(message: dict) -> list[ToolCall]:
        calls = []
        for c in message.get("tool_calls") or []:
            fn = c.get("function") or {}
            raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw)
                if not isinstance(args, dict):
                    raise ValueError("arguments not an object")
                err = ""
            except (json.JSONDecodeError, ValueError):
                args, err = {}, str(raw)[:500]
            calls.append(
                ToolCall(id=c.get("id") or "", name=fn.get("name") or "", arguments=args,
                         parse_error=err)
            )
        return calls

    # -- protocol -----------------------------------------------------------

    def run_turn(self, system: str, messages: list[dict], tools: list[dict]) -> TurnResult:
        self._pacer.wait()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict = {
            "model": self.model,
            "messages": self._translate_history(system, messages),
            "tools": self._translate_tools(tools),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        data = _post_json(f"{self.base_url}/chat/completions", headers, payload, self.name)
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError) as e:
            raise BackendError(f"{self.name}: malformed response: {str(data)[:300]}") from e
        usage = data.get("usage") or {}
        calls = self._parse_calls(message)
        finish = choice.get("finish_reason") or "stop"
        return TurnResult(
            text=message.get("content") or "",
            tool_calls=calls,
            input_tokens=usage.get("prompt_tokens") or 0,
            output_tokens=usage.get("completion_tokens") or 0,
            stop_reason="tool_calls" if calls else ("length" if finish == "length" else "stop"),
        )


class AnthropicAgentBackend:
    """Native Messages API adapter (tool_use / tool_result blocks). The bridge
    backend: the same Claude model run here and in-product ties the two
    evidence branches together (ADR-0009)."""

    name = "anthropic_api"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        model: str,
        api_key: str = "",
        temperature: float | None = 0.0,
        max_tokens: int = 8192,
        rpm: float | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._pacer = _Pacer(rpm)

    @staticmethod
    def _translate_tools(tools: list[dict]) -> list[dict]:
        return [
            {"name": t["name"], "description": t["description"],
             "input_schema": t["parameters"]}
            for t in tools
        ]

    @staticmethod
    def _translate_history(messages: list[dict]) -> list[dict]:
        """Neutral -> Messages API. Consecutive tool results collapse into one
        user turn (the API requires tool_result blocks to open the next user
        message)."""
        wire: list[dict] = []
        for m in messages:
            if m["role"] == "assistant":
                blocks: list[dict] = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for c in m.get("tool_calls") or []:
                    blocks.append(
                        {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    )
                wire.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            elif m["role"] == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }
                if m.get("is_error"):
                    block["is_error"] = True
                if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list) \
                        and wire[-1]["content"] and wire[-1]["content"][0].get("type") == "tool_result":
                    wire[-1]["content"].append(block)
                else:
                    wire.append({"role": "user", "content": [block]})
            else:
                wire.append({"role": "user", "content": m["content"]})
        return wire

    def run_turn(self, system: str, messages: list[dict], tools: list[dict]) -> TurnResult:
        self._pacer.wait()
        if not self.api_key:
            raise BackendError(f"{self.name}: ANTHROPIC_API_KEY not set")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": self._translate_history(messages),
            "tools": self._translate_tools(tools),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        data = _post_json(self.API_URL, headers, payload, self.name)
        if data.get("type") == "error":
            raise BackendError(f"{self.name}: {str(data.get('error'))[:300]}")
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text_parts.append(block.get("text") or "")
            elif block.get("type") == "tool_use":
                args = block.get("input")
                calls.append(
                    ToolCall(
                        id=block.get("id") or "",
                        name=block.get("name") or "",
                        arguments=args if isinstance(args, dict) else {},
                        parse_error="" if isinstance(args, dict) else str(args)[:500],
                    )
                )
        usage = data.get("usage") or {}
        stop = data.get("stop_reason") or "end_turn"
        return TurnResult(
            text="\n".join(t for t in text_parts if t),
            tool_calls=calls,
            input_tokens=usage.get("input_tokens") or 0,
            output_tokens=usage.get("output_tokens") or 0,
            stop_reason="tool_calls" if calls else ("length" if stop == "max_tokens" else "stop"),
        )


# --------------------------------------------------------------------------

# preset -> (base_url, api-key env var). "anthropic" is handled natively.
PRESETS: dict[str, tuple[str, str | None]] = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    # same OpenAI-compat endpoint judge.py already uses for the Gemini judge
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "local": ("http://localhost:11434/v1", None),
}


def make_backend(
    kind: str,
    model: str,
    base_url: str | None = None,
    temperature: float | None = 0.0,
    rpm: float | None = None,
):
    """Build an AgentBackend from a CLI preset. `openai-compat` + --base-url is
    the generic escape hatch (key via LOOP_API_KEY, optional)."""
    if kind == "anthropic":
        return AnthropicAgentBackend(model=model, temperature=temperature, rpm=rpm)
    if kind == "openai-compat":
        if not base_url:
            raise BackendError("openai-compat requires --base-url")
        return OpenAICompatAgentBackend(
            base_url, model, api_key=os.environ.get("LOOP_API_KEY", ""),
            temperature=temperature, rpm=rpm,
        )
    if kind not in PRESETS:
        raise BackendError(
            f"unknown backend '{kind}' — choose from "
            f"{', '.join([*PRESETS, 'anthropic', 'openai-compat'])}"
        )
    url, key_env = PRESETS[kind]
    api_key = os.environ.get(key_env, "") if key_env else ""
    if key_env and not api_key:
        raise BackendError(f"{kind}: {key_env} not set")
    backend = OpenAICompatAgentBackend(
        base_url or url, model, api_key=api_key, temperature=temperature, rpm=rpm
    )
    backend.name = f"openai_compat/{kind}"
    return backend
