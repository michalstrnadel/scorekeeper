"""Subprocess-level E2E: the process contract of the CLI.

Semantics (gate modes, wall-vs-bump, operator outcomes) are covered in-process
by test_tier0_gate.py / test_cli_hooks.py / test_mcp_server.py. What no
in-process test can prove is exercised here: real argv/stdin/stdout/exit-code
through ``python -m scorekeeper``, with a fresh process reading state purely
from disk between steps.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from scorekeeper import Store
from scorekeeper.extract import ExtractedCommitment
from scorekeeper.operators import apply


def run_cli(
    args: list[str], stdin: str = "", cwd: str | None = None
) -> subprocess.CompletedProcess:
    """Run the real CLI in a scrubbed env — a developer's SCOREKEEPER_* shell
    vars (e.g. SCOREKEEPER_TIER0_GATE) must not leak into the assertion."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SCOREKEEPER_")}
    return subprocess.run(
        [sys.executable, "-m", "scorekeeper", *args],
        input=stdin, capture_output=True, text=True, cwd=cwd, env=env, timeout=60,
    )


def hook(event: str, payload: dict) -> subprocess.CompletedProcess:
    return run_cli(["hook", event], stdin=json.dumps(payload))


def seed(root, claim: str, value: str) -> None:
    apply(Store(root), [ExtractedCommitment(
        claim=claim,
        kind="decision",
        scope=["topic:persistence", f"attr:persistence.primary_db={value}"],
        entitlement={"source": "user_utterance", "note": "user decided"},
    )])


def test_gate_chain_deny_wall_supersede_pass(tmp_path):
    store = Store(tmp_path)
    store.init()
    (store.dir / "config.yaml").write_text("tier0_gate: block\n")
    seed(tmp_path, "The primary database is PostgreSQL 16.", "postgresql")

    drift = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "app" / "db.py"),
                       "content": "import pymongo  # switch to mongodb"},
    }

    # 1. conflicting write -> deny JSON on stdout, exit 0 (never non-zero)
    first = hook("pre-tool-use", drift)
    assert first.returncode == 0, first.stderr
    decision = json.loads(first.stdout)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"

    # 2. the wall: an identical retry in a FRESH process is still denied —
    # deny state and scoreboard are read purely from disk
    second = hook("pre-tool-use", drift)
    assert second.returncode == 0
    assert json.loads(second.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"

    # 3. the board records the entitled revision (deterministic supersede)
    seed(tmp_path, "The primary database is MongoDB.", "mongodb")

    # 4. the same payload now passes: empty stdout, exit 0
    third = hook("pre-tool-use", drift)
    assert third.returncode == 0, third.stderr
    assert third.stdout.strip() == ""


def test_hook_never_exits_nonzero_on_garbage(tmp_path):
    # run.sh treats any non-zero exit as infrastructure failure (#6) — the CLI
    # must hold exit 0 even on garbage input, with diagnostics on stderr only
    for stdin in ("not json", "", '{"cwd": 42}'):
        result = run_cli(["hook", "pre-tool-use"], stdin=stdin, cwd=str(tmp_path))
        assert result.returncode == 0, (stdin, result.stderr)
        assert result.stdout.strip() == ""


def test_cli_init_and_report_roundtrip(tmp_path):
    init = run_cli(["init", "--root", str(tmp_path)])
    assert init.returncode == 0, init.stderr
    seed(tmp_path, "The primary database is PostgreSQL 16.", "postgresql")
    report = run_cli(["report", "--root", str(tmp_path)])
    assert report.returncode == 0, report.stderr
    assert "PostgreSQL 16" in report.stdout
