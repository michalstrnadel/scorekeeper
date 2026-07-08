"""scorekeeper CLI — hook handlers + human commands.

Hook contract (Claude Code): JSON on stdin, JSON on stdout, exit 0. Handlers
NEVER raise — a broken scorer must not break the agent (errors go to the audit
log and stderr). The agent has no write authority here: hooks are the only
door (scaffolded, not extended — theory.md §5).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from .backends import BackendError, detect_backend
from .detect import tier0_content
from .extract import build_turn_text, extract_commitments
from .operators import apply
from .store import Store
from .transcript import read_last_turn


def _root(payload: dict) -> Path:
    return Path(payload.get("cwd") or Path.cwd())


def _read_payload() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _emit(obj: dict) -> None:
    print(json.dumps(obj))


# -- hook handlers -------------------------------------------------------------


def hook_session_start(payload: dict) -> None:
    store = Store(_root(payload))
    digest = store.render_digest()
    if not digest:
        return
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": digest,
            }
        }
    )


def hook_post_tool_use(payload: dict) -> None:
    store = Store(_root(payload))
    if not store.exists:
        return
    tool_input = payload.get("tool_input") or {}
    content = " ".join(
        str(tool_input.get(k, "")) for k in ("content", "new_string", "old_string")
    ).strip()
    if not content:
        return
    warnings = tier0_content.scan(content, store.active())
    if not warnings:
        return
    for w in warnings:
        store.log(
            "TIER0-CONTENT-WARNING",
            w.commitment_id,
            f"{w.key}={w.pinned_value} vs '{w.rival_found}' in {tool_input.get('file_path', '?')}",
        )
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": tier0_content.format_warnings(warnings),
            }
        }
    )


def hook_stop(payload: dict) -> None:
    if payload.get("stop_hook_active"):
        return  # already inside a stop-hook continuation — never loop
    root = _root(payload)
    store = Store(root)
    transcript_path = payload.get("transcript_path", "")
    if not transcript_path or not Path(transcript_path).exists():
        return
    turn = read_last_turn(transcript_path)
    if turn.empty:
        return

    store.init()
    try:
        backend = detect_backend(root)
    except BackendError as e:
        store.log("ERROR", detail=f"stop-hook: no backend: {e}")
        return

    errors: list[str] = []
    extracted = extract_commitments(
        backend,
        build_turn_text(turn.user_text, turn.assistant_text, turn.tools_used),
        digest=store.render_digest(),
        on_error=lambda e: errors.append(str(e)),
    )
    for err in errors:
        store.log("ERROR", detail=f"stop-hook extraction: {err[:300]}")
    if not extracted:
        return

    session = payload.get("session_id", "")
    result = apply(store, extracted, backend=backend, session=session, refs=[f"session:{session}"])

    if not result.has_findings:
        return
    lines: list[str] = []
    for conflict in result.conflicts:
        old = store.load(conflict.existing_id)
        new = store.load(conflict.new_id)
        lines.append(
            f"COMMITMENT CONFLICT: you are committed to '{old.claim}' ({old.id}) but this turn "
            f"produced '{new.claim}' without entitlement to revise ({conflict.reason}). "
            "Surface this to the user and resolve it before building on either."
        )
    for cid in result.challenges:
        c = store.load(cid)
        lines.append(
            f"UNBACKED CLAIM: '{c.claim}' ({c.id}) has no provenance — no user statement, file "
            "read, or tool output backs it. Verify it (read the source) or retract it."
        )
    _emit({"decision": "block", "reason": "\n".join(lines)})


def hook_pre_compact(payload: dict) -> None:
    store = Store(_root(payload))
    if not store.exists:
        return
    backup_dir = store.dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    store.write_scoreboard()
    shutil.copy2(store.scoreboard_path, backup_dir / f"scoreboard-{stamp}.md")
    store.log("PRECOMPACT-BACKUP", detail=str(backup_dir / f"scoreboard-{stamp}.md"))


HOOKS = {
    "session-start": hook_session_start,
    "post-tool-use": hook_post_tool_use,
    "stop": hook_stop,
    "pre-compact": hook_pre_compact,
}


# -- human commands --------------------------------------------------------------


def cmd_init(root: Path) -> None:
    store = Store(root)
    store.init()
    store.write_scoreboard()
    print(f"initialized {store.dir}")


def cmd_digest(root: Path) -> None:
    print(Store(root).render_digest())


def cmd_report(root: Path) -> None:
    print(Store(root).render_scoreboard())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scorekeeper")
    sub = parser.add_subparsers(dest="command", required=True)
    hook_p = sub.add_parser("hook", help="Claude Code hook handler (JSON on stdin)")
    hook_p.add_argument("event", choices=sorted(HOOKS))
    for name in ("init", "digest", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=".", help="project root (default: cwd)")
    args = parser.parse_args(argv)

    if args.command == "hook":
        payload = _read_payload()
        try:
            HOOKS[args.event](payload)
        except Exception as e:  # noqa: BLE001 — a broken scorer must never break the agent
            print(f"scorekeeper {args.event} error: {e}", file=sys.stderr)
            with contextlib.suppress(Exception):
                Store(_root(payload)).log("ERROR", detail=f"{args.event}: {e}")
        return 0

    root = Path(args.root)
    {"init": cmd_init, "digest": cmd_digest, "report": cmd_report}[args.command](root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
