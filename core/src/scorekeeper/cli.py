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
    if payload.get("tool_name") == "Bash":
        # log-only audit of shell writes — this is what makes the wall's
        # "every workaround is audited" deterrent true (no warning to the
        # agent: `grep memcached` is not drift)
        command = str(tool_input.get("command", "")).strip()
        if not command:
            return None
        for w in tier0_content.scan(command, store.active(), exhaustive=True):
            store.log(
                "TIER0-SHELL-AUDIT",
                w.commitment_id,
                f"{w.key}={w.pinned_value} vs '{w.rival_found}' in shell command",
            )
        return None
    # advisory scope twin (ADR-0008): a landed out-of-scope write is logged and
    # surfaced regardless of gate mode — the audit floor under the wall
    lines: list[str] = []
    target = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if target:
        sd = tier0_gate.evaluate_scope(target, store.active(), _root(payload))
        if sd is not None:
            for cid in dict.fromkeys(p.commitment_id for p in sd.pins):
                store.log(
                    "TIER0-SCOPE-WARNING", cid, f"'{sd.target}' outside pinned write scope"
                )
            lines.append(tier0_gate.format_scope_warning(sd.target, sd.pins))
    content = " ".join(
        str(tool_input.get(k, "")) for k in ("content", "new_string", "new_source")
    ).strip()
    if content:
        warnings = tier0_content.scan(content, store.active())
        # a rival already in old_string is not NEW: an edit REMOVING the rival
        # (drift being fixed) must not warn (audit finding 2026-07-14)
        warnings = tier0_content.novel(
            warnings, str(tool_input.get("old_string", "")), store.active()
        )
        for w in warnings:
            store.log(
                "TIER0-CONTENT-WARNING",
                w.commitment_id,
                f"{w.key}={w.pinned_value} vs '{w.rival_found}'"
                f" in {tool_input.get('file_path', '?')}",
            )
        if warnings:
            lines.append(tier0_content.format_warnings(warnings))
    if not lines:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(lines),
        }
    }


def hook_pre_tool_use(payload: dict) -> dict | None:
    """Blocking Tier-0 gate (ADR-0007). Mode ``block`` (v2): the deny stands
    while the pinned commitment is active — only the board recording an
    entitled SUPERSEDE lifts it. Mode ``bump`` (v1 ablation): deny once per
    (commitment, rival) pair, instructed retry passes. Opt-in via
    SCOREKEEPER_TIER0_GATE=block|bump (env) or ``tier0_gate: block|bump`` in
    .scorekeeper/config.yaml — advisory PostToolUse warnings stay the
    default channel."""
    store = Store(_root(payload))
    if not store.exists:
        return None
    mode = _gate_mode(store)
    tool_input = payload.get("tool_input") or {}
    # scope wall (ADR-0008) runs FIRST: it gates the TARGET, so the doc
    # exemption below (a claims-content concern) and the empty-content bail
    # must not shadow it — a drive-by README edit or an empty new file
    # outside the entitled scope is still barging
    target = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if target and _scope_mode(store):
        sd = tier0_gate.evaluate_scope(target, store.active(), _root(payload))
        if sd is not None:
            for cid in dict.fromkeys(p.commitment_id for p in sd.pins):
                store.log(
                    "TIER0-SCOPE-DENY", cid,
                    f"'{sd.target}' outside pinned write scope", mode="block",
                )
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": sd.reason,
                }
            }
    if not mode:
        return None
    # the gate blocks CODE drift; prose that argues about the rival ("Memcached
    # was evaluated and rejected") lives in docs, where a hard deny is pure FPR
    # (audit finding 2026-07-14) — the advisory PostToolUse warning still fires
    if str(tool_input.get("file_path", "")).endswith(_GATE_EXEMPT_SUFFIXES):
        return None
    content = " ".join(
        str(tool_input.get(k, "")) for k in ("content", "new_string", "new_source")
    ).strip()
    if not content:
        return None
    baseline = str(tool_input.get("old_string", ""))
    if mode == "block":
        decision = tier0_gate.evaluate_wall(content, store.active(), baseline=baseline)
    else:
        decision = tier0_gate.evaluate(
            content, store.active(), store.dir / tier0_gate.STATE_FILENAME, baseline=baseline
        )
    if decision is None:
        return None
    for w in decision.warnings:
        store.log(
            "TIER0-GATE-DENY",
            w.commitment_id,
            f"{w.key}={w.pinned_value} vs '{w.rival_found}' in {tool_input.get('file_path', '?')}",
            mode=mode,
        )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": decision.reason,
        }
    }


# documentation suffixes exempt from the blocking gate (advisory channel only)
_GATE_EXEMPT_SUFFIXES = (".md", ".rst", ".txt")


def _gate_mode(store: Store) -> str:
    """'' (off) | 'block' (v2 wall) | 'bump' (v1 speed bump). Env OVERRIDES
    config in both directions: block/bump force-enable that mode, "warn"
    force-disables (advisory only) even if config enables the gate."""
    mode = os.environ.get("SCOREKEEPER_TIER0_GATE", "")
    if mode in ("block", "bump"):
        return mode
    if mode == "warn":
        return ""
    cfg = store.dir / "config.yaml"
    if cfg.exists():
        with contextlib.suppress(Exception):
            data = yaml.safe_load(cfg.read_text()) or {}
            if data.get("tier0_gate") in ("block", "bump"):
                return data["tier0_gate"]
    return ""


def _scope_mode(store: Store) -> str:
    """'' (off) | 'block'. The scope wall (ADR-0008) rides the claim gate: it
    is active whenever ``tier0_gate`` is enabled (block OR bump — scope is
    wall-only either way; the bump's retry channel was exploited on claims).
    Independent kill switch for ablation/emergencies: SCOREKEEPER_SCOPE_GATE=off
    or ``scope_gate: off`` disables just the scope wall; =block force-enables
    it even with the claim gate off. Env overrides config, like _gate_mode."""
    mode = os.environ.get("SCOREKEEPER_SCOPE_GATE", "")
    if mode == "block":
        return "block"
    if mode == "off":
        return ""
    cfg = store.dir / "config.yaml"
    if cfg.exists():
        with contextlib.suppress(Exception):
            data = yaml.safe_load(cfg.read_text()) or {}
            val = data.get("scope_gate")
            # YAML 1.1 reads a bare `off` as boolean False — accept both spellings
            if val == "off" or val is False:
                return ""
            if val == "block":
                return "block"
    return "block" if _gate_mode(store) else ""


def _extract_mode(root: Path) -> str:
    """``sync`` (default: findings block the turn) or ``async`` (detached worker,
    findings injected on the next user prompt — ADR-0006, latency-first).

    Precedence: SCOREKEEPER_EXTRACT (user env) > config ``extract:`` >
    SCOREKEEPER_EXTRACT_DEFAULT (surface default — the plugin's hooks.json
    sets it to async WITHOUT shadowing the config key) > ``sync``."""
    mode = os.environ.get("SCOREKEEPER_EXTRACT", "")
    if mode in ("sync", "async"):
        return mode
    cfg = Store(root).dir / "config.yaml"
    if cfg.exists():
        with contextlib.suppress(Exception):
            data = yaml.safe_load(cfg.read_text()) or {}
            if data.get("extract") in ("sync", "async"):
                return data["extract"]
    default = os.environ.get("SCOREKEEPER_EXTRACT_DEFAULT", "")
    if default in ("sync", "async"):
        return default
    return "sync"


def _extract_findings(store: Store, payload: dict) -> list[str]:
    """Extract the last turn, run the operators, return findings lines.
    Shared by the sync stop hook and the detached worker. Runs the LLM
    extraction outside any lock — ``apply()`` takes the store's write lock
    itself for the write phase, so callers must pass THE store instance they
    coordinate on, not re-derive one (per-instance lock re-entrancy)."""
    root = store.root
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
    # no outer lock: the LLM extraction must not serialize other writers for
    # tens of seconds — apply() takes the write lock itself for the write phase
    lines = _extract_findings(Store(root), payload)
    if not lines:
        return None
    return {"decision": "block", "reason": "\n".join(lines)}


def hook_user_prompt_submit(payload: dict) -> dict | None:
    """Drain findings produced by async workers into the next turn's context."""
    store = Store(_root(payload))
    pending = store.dir / "pending-findings.md"
    if not pending.exists():
        return None
    try:
        # same lock the worker appends under — an unlocked read+unlink deleted
        # findings appended in between (audit 2026-07-14). Non-blocking: if a
        # worker is mid-extraction (seconds of LLM), skip; next prompt drains.
        with store.write_lock(blocking=False):
            text = pending.read_text().strip()
            pending.unlink()
    except OSError:
        return None
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
    # nothing to protect on an empty store — and regenerating would clobber a
    # hand-maintained scoreboard.md (this repo's own board, pre-MVP convention)
    if not store.all():
        return None
    try:
        # non-blocking: a worker mid-apply() holds the lock, and a backup
        # snapshotting a half-applied transition (old record SUPERSEDED, new
        # one not yet saved) is worse than skipping this compaction's backup
        with store.write_lock(blocking=False):
            backup_dir = store.dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            store.write_scoreboard()
            shutil.copy2(store.scoreboard_path, backup_dir / f"scoreboard-{stamp}.md")
            store.log("PRECOMPACT-BACKUP", detail=str(backup_dir / f"scoreboard-{stamp}.md"))
    except BlockingIOError:
        return None
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
        # extraction (LLM, possibly minutes) runs unlocked; apply() locks its
        # own write phase. Only the findings append needs the lock here — it
        # is coordinated with the prompt-submit drain's non-blocking read.
        lines = _extract_findings(store, payload)
        if lines:
            with store.write_lock():
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
    # don't regenerate over an existing board (it may be hand-maintained);
    # every write path refreshes it anyway
    if not store.scoreboard_path.exists():
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
                store = Store(_root(payload))
                if store.exists:  # best-effort audit; never create .scorekeeper/ just to log
                    store.log("ERROR", detail=f"{args.event}: {e}")
        return 0

    root = Path(args.root)
    {"init": cmd_init, "digest": cmd_digest, "report": cmd_report}[args.command](root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
