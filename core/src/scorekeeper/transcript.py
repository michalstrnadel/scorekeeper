"""Tolerant Claude Code transcript (JSONL) reader — last-turn extraction.

The Stop hook receives ``transcript_path``; we need the final turn: the last
real user message (not a tool_result), everything the assistant said after it,
and the tools it used. The format has minor variations across versions, so
parsing is defensive: unknown lines are skipped, missing fields default.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Turn:
    user_text: str = ""
    assistant_text: str = ""
    tools_used: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.user_text or self.assistant_text)


def _content_blocks(message: dict) -> list:
    content = message.get("content", [])
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def _tool_label(block: dict) -> str:
    name = block.get("name", "?")
    inp = block.get("input") or {}
    for key in ("file_path", "path", "command", "pattern", "url"):
        if key in inp:
            detail = str(inp[key])
            return f"{name}({detail[:120]})"
    return name


def read_last_turn(path: Path | str) -> Turn:
    lines = Path(path).read_text().splitlines()
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # find the last REAL user message (text content, not tool_result)
    last_user_idx = None
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if e.get("type") != "user":
            continue
        blocks = _content_blocks(e.get("message", {}))
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        if any(t.strip() for t in texts):
            last_user_idx = i
            break

    turn = Turn()
    if last_user_idx is None:
        return turn

    blocks = _content_blocks(entries[last_user_idx].get("message", {}))
    turn.user_text = "\n".join(
        b.get("text", "") for b in blocks if b.get("type") == "text"
    ).strip()

    assistant_parts: list[str] = []
    for e in entries[last_user_idx + 1 :]:
        if e.get("type") != "assistant":
            continue
        for b in _content_blocks(e.get("message", {})):
            btype = b.get("type")
            if btype == "text" and b.get("text", "").strip():
                assistant_parts.append(b["text"].strip())
            elif btype == "tool_use":
                turn.tools_used.append(_tool_label(b))
    turn.assistant_text = "\n\n".join(assistant_parts)
    return turn
