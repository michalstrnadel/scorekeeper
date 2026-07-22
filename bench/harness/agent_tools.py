"""Tool belt for the reference agent loop (ADR-0009).

Tools are named and shaped identically to Claude Code's — the hook payloads
the loop synthesizes ({tool_name, tool_input, cwd}) must match what the
plugin's hook_pre_tool_use / hook_post_tool_use already parse (file_path,
content, new_string, command), so the wall and the audit run unmodified.

Every path is resolved and confined to the workdir: the loop refuses root
escapes rather than relying on the model's manners (F13's lesson — turn-1 was
unwalled in-product because enforcement trusted the harness edge).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

BASH_TIMEOUT_S = 60
READ_MAX_LINES = 2000
READ_MAX_LINE_CHARS = 500
OUTPUT_CAP_CHARS = 30_000


class ToolError(Exception):
    """User-level tool failure — returned to the model as an error result."""


# OpenAI function-calling shape; AnthropicAgentBackend translates to
# input_schema. Descriptions stay terse: they are part of the controlled
# system surface and must not coach any model toward or away from the barge.
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "Read",
        "description": "Read a file. Returns numbered lines.",
        "parameters": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "Write",
        "description": "Write a file (create or overwrite). Creates parent directories.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "Edit",
        "description": (
            "Replace old_string with new_string in a file. old_string must match "
            "exactly and be unique unless replace_all is true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
    {
        "name": "Glob",
        "description": "List files matching a glob pattern, relative to the project root.",
        "parameters": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "Grep",
        "description": "Search file contents with a regular expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "Bash",
        "description": f"Run a shell command in the project root (timeout {BASH_TIMEOUT_S}s).",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]

TOOL_NAMES = {t["name"] for t in TOOL_SCHEMAS}


def _resolve(workdir: Path, raw: str) -> Path:
    """Resolve a model-supplied path and confine it to the workdir."""
    if not raw:
        raise ToolError("file_path is required")
    p = Path(raw)
    candidate = (p if p.is_absolute() else workdir / p).resolve()
    root = workdir.resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolError(f"path escapes the project root: {raw}")
    return candidate


def _read(workdir: Path, args: dict) -> str:
    path = _resolve(workdir, str(args.get("file_path", "")))
    if not path.is_file():
        raise ToolError(f"not a file: {args.get('file_path')}")
    try:
        text = path.read_text()
    except UnicodeDecodeError as e:
        raise ToolError(f"not a text file: {args.get('file_path')}") from e
    lines = text.splitlines()
    shown = [
        f"{i:6d}\t{line[:READ_MAX_LINE_CHARS]}"
        for i, line in enumerate(lines[:READ_MAX_LINES], 1)
    ]
    if len(lines) > READ_MAX_LINES:
        shown.append(f"... (truncated: {len(lines) - READ_MAX_LINES} more lines)")
    return "\n".join(shown) if shown else "(empty file)"


def _write(workdir: Path, args: dict) -> str:
    path = _resolve(workdir, str(args.get("file_path", "")))
    content = args.get("content")
    if content is None:
        raise ToolError("content is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content))
    return f"wrote {len(str(content))} chars to {path.relative_to(workdir.resolve())}"


def _edit(workdir: Path, args: dict) -> str:
    path = _resolve(workdir, str(args.get("file_path", "")))
    if not path.is_file():
        raise ToolError(f"not a file: {args.get('file_path')}")
    old = str(args.get("old_string", ""))
    new = str(args.get("new_string", ""))
    if not old:
        raise ToolError("old_string is required")
    if old == new:
        raise ToolError("old_string and new_string are identical")
    text = path.read_text()
    n = text.count(old)
    if n == 0:
        raise ToolError("old_string not found in file")
    if n > 1 and not args.get("replace_all"):
        raise ToolError(f"old_string matches {n} times — pass replace_all or disambiguate")
    path.write_text(text.replace(old, new))
    return f"replaced {n if args.get('replace_all') else 1} occurrence(s)"


def _glob(workdir: Path, args: dict) -> str:
    pattern = str(args.get("pattern", "")).lstrip("/")
    if not pattern:
        raise ToolError("pattern is required")
    root = workdir.resolve()
    matches = sorted(
        str(p.relative_to(root)) for p in root.glob(pattern) if p.is_file()
    )
    return "\n".join(matches) if matches else "(no matches)"


def _grep(workdir: Path, args: dict) -> str:
    pattern = str(args.get("pattern", ""))
    if not pattern:
        raise ToolError("pattern is required")
    try:
        rx = re.compile(pattern)
    except re.error as e:
        raise ToolError(f"bad regex: {e}") from e
    root = workdir.resolve()
    base = _resolve(workdir, str(args["path"])) if args.get("path") else root
    files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
    hits: list[str] = []
    for f in files:
        try:
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f.relative_to(root)}:{i}:{line[:200]}")
                    if len(hits) >= 200:
                        return "\n".join(hits) + "\n... (capped at 200 hits)"
        except (UnicodeDecodeError, OSError):
            continue
    return "\n".join(hits) if hits else "(no matches)"


def _bash(workdir: Path, args: dict) -> str:
    command = str(args.get("command", "")).strip()
    if not command:
        raise ToolError("command is required")
    try:
        proc = subprocess.run(
            ["/bin/bash", "-c", command],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=BASH_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError(f"command timed out after {BASH_TIMEOUT_S}s") from e
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    out = out.strip() or "(no output)"
    if proc.returncode != 0:
        out += f"\n(exit code {proc.returncode})"
    return out


_HANDLERS = {
    "Read": _read,
    "Write": _write,
    "Edit": _edit,
    "Glob": _glob,
    "Grep": _grep,
    "Bash": _bash,
}


def execute(workdir: Path, name: str, arguments: dict) -> str:
    """Run one tool call. Raises ToolError for user-level failures; the loop
    formats those as error tool-results (the model sees them, the run
    continues)."""
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"unknown tool: {name}")
    result = handler(workdir, arguments or {})
    if len(result) > OUTPUT_CAP_CHARS:
        result = result[:OUTPUT_CAP_CHARS] + "\n... (output truncated)"
    return result
