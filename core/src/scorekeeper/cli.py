"""scorekeeper CLI — hook handlers + human commands.

Hook contract (Claude Code): JSON on stdin, JSON on stdout, exit 0. Handlers
NEVER raise — a broken scorer must not break the agent (errors go to the audit
log and stderr). The agent has no write authority here: hooks are the only
door (scaffolded, not extended — theory.md §5).
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .backends import BackendError, detect_backend
from .detect import tier0_content, tier0_gate
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


def hook_session_start(payload: dict) -> dict | None:
    store = Store(_root(payload))
    digest = store.render_digest()
    if not digest:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": digest,
        }
    }


def hook_post_tool_use(payload: dict) -> dict | None:
    store = Store(_root(payload))
    if not store.exists:
        return None
    tool_input = payload.get("tool_input") or {}
    content = " ".join(
        str(tool_input.get(k, "")) for k in ("content", "new_string", "old_string")
    ).strip()
    if not content:
        return None
    warnings = tier0_content.scan(content, store.active())
    if not warnings:
        return None
    for w in warnings:
        store.log(
            "TIER0-CONTENT-WARNING",
            w.commitment_id,
            f"{w.key}={w.pinned_value} vs '{w.rival_found}' in {tool_input.get('file_path', '?')}",
        )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": tier0_content.format_warnings(warnings),
        }
    }


def hook_pre_tool_use(payload: dict) -> dict | None:
    """Blocking Tier-0 gate (ADR-0007): deny the FIRST rival-tech write per
    (commitment, rival) pair with a reason that forces the conflict into the
    agent's context; retries pass. Opt-in via SCOREKEEPER_TIER0_GATE=block
    (env) or ``tier0_gate: block`` in .scorekeeper/config.yaml — advisory
    PostToolUse warnings stay the default channel."""
    store = Store(_root(payload))
    if not store.exists or not _gate_enabled(store):
        return None
    tool_input = payload.get("tool_input") or {}
    content = " ".join(
        str(tool_input.get(k, "")) for k in ("content", "new_string")
    ).strip()
    if not content:
        return None
    decision = tier0_gate.evaluate(content, store.active(), store.dir / tier0_gate.STATE_FILENAME)
    if decision is None:
        return None
    for w in decision.warnings:
        store.log(
            "TIER0-GATE-DENY",
            w.commitment_id,
            f"{w.key}={w.pinned_value} vs '{w.rival_found}' in {tool_input.get('file_path', '?')}",
        )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": decision.reason,
        }
    }


def _gate_enabled(store: Store) -> bool:
    mode = os.environ.get("SCOREKEEPER_TIER0_GATE", "")
    if mode in ("block", "warn"):
        return mode == "block"
    cfg = store.dir / "config.yaml"
    if cfg.exists():
        with contextlib.suppress(Exception):
            data = yaml.safe_load(cfg.read_text()) or {}
            return data.get("tier0_gate") == "block"
    return False


def _extract_mode(root: Path) -> str:
    """``sync`` (default: findings block the turn) or ``async`` (detached worker,
    findings injected on the next user prompt — ADR-0006, latency-first)."""
    mode = os.environ.get("SCOREKEEPER_EXTRACT", "")
    if mode in ("sync", "async"):
        return mode
    cfg = Store(root).dir / "config.yaml"
    if cfg.exists():
        with contextlib.suppress(Exception):
            data = yaml.safe_load(cfg.read_text()) or {}
            if data.get("extract") in ("sync", "async"):
                return data["extract"]
    return "sync"


def _extract_findings(root: Path, payload: dict) -> list[str]:
    """Extract the last turn, run the operators, return findings lines.
    Shared by the sync stop hook and the detached worker."""
    store = Store(root)
    turn = read_last_turn(payload["transcript_path"])
    if turn.empty:
        return []
    store.init()
    try:
        backend = detect_backend(root)
    except BackendError as e:
        store.log("ERROR", detail=f"stop-hook: no backend: {e}")
        return []

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
        return []

    session = payload.get("session_id", "")
    result = apply(store, extracted, backend=backend, session=session, refs=[f"session:{session}"])

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
    return lines


def _spawn_worker(root: Path, payload: dict) -> None:
    """Detach extraction into a worker process; the hook returns immediately."""
    store = Store(root)
    workdir = store.dir / "worker"
    workdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    payload_path = workdir / f"payload-{stamp}-{os.getpid()}.json"
    payload_path.write_text(json.dumps(payload))
    with (workdir / "worker.log").open("a") as log_file:
        subprocess.Popen(
            [sys.executable, "-m", "scorekeeper", "worker", str(payload_path)],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
            cwd=str(root),
        )


def hook_stop(payload: dict) -> dict | None:
    if payload.get("stop_hook_active"):
        return None  # already inside a stop-hook continuation — never loop
    root = _root(payload)
    transcript_path = payload.get("transcript_path", "")
    if not transcript_path or not Path(transcript_path).exists():
        return None
    if _extract_mode(root) == "async":
        Store(root).init()
        _spawn_worker(root, payload)
        return None
    lines = _extract_findings(root, payload)
    if not lines:
        return None
    return {"decision": "block", "reason": "\n".join(lines)}


def hook_user_prompt_submit(payload: dict) -> dict | None:
    """Drain findings produced by async workers into the next turn's context."""
    store = Store(_root(payload))
    pending = store.dir / "pending-findings.md"
    if not pending.exists():
        return None
    text = pending.read_text().strip()
    pending.unlink()
    if not text:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }


def hook_pre_compact(payload: dict) -> dict | None:
    store = Store(_root(payload))
    if not store.exists:
        return None
    backup_dir = store.dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    store.write_scoreboard()
    shutil.copy2(store.scoreboard_path, backup_dir / f"scoreboard-{stamp}.md")
    store.log("PRECOMPACT-BACKUP", detail=str(backup_dir / f"scoreboard-{stamp}.md"))
    return None


HOOKS = {
    "session-start": hook_session_start,
    "pre-tool-use": hook_pre_tool_use,
    "post-tool-use": hook_post_tool_use,
    "user-prompt-submit": hook_user_prompt_submit,
    "stop": hook_stop,
    "pre-compact": hook_pre_compact,
}


def cmd_worker(payload_path: Path) -> None:
    """Detached async-extraction worker (spawned by the stop hook, ADR-0006).

    Serialized per store via flock — concurrent sessions on one repo must not
    interleave id allocation or scoreboard writes."""
    try:
        payload = json.loads(payload_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"scorekeeper worker: unreadable payload {payload_path}: {e}", file=sys.stderr)
        payload_path.unlink(missing_ok=True)
        return
    root = _root(payload)
    store = Store(root)
    store.init()
    try:
        with (store.dir / "worker.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            lines = _extract_findings(root, payload)
            if lines:
                with (store.dir / "pending-findings.md").open("a") as f:
                    f.write("\n".join(lines) + "\n")
                store.log("ASYNC-FINDINGS", detail=f"{len(lines)} pending finding(s)")
    except Exception as e:  # noqa: BLE001 — detached; log, never propagate
        with contextlib.suppress(Exception):
            store.log("ERROR", detail=f"worker: {e}")
    finally:
        payload_path.unlink(missing_ok=True)


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
    worker_p = sub.add_parser("worker", help="async extraction worker (internal)")
    worker_p.add_argument("payload_file")
    for name in ("init", "digest", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=".", help="project root (default: cwd)")
    args = parser.parse_args(argv)

    if args.command == "worker":
        cmd_worker(Path(args.payload_file))
        return 0

    if args.command == "hook":
        payload = _read_payload()
        try:
            result = HOOKS[args.event](payload)
            if result:
                _emit(result)
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
