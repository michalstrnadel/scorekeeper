"""Blocking Tier-0 gate (ADR-0007) — deny once, let the retry pass."""

import json
from datetime import UTC, datetime

from test_cli_hooks import FakeStdin, run_hook, seed_commitment  # noqa: F401

from scorekeeper import Commitment, Entitlement, EntitlementSource, Kind, Store
from scorekeeper.detect import tier0_gate

MONGO_EDIT = {
    "tool_name": "Write",
    "tool_input": {
        "file_path": "app/db.py",
        "content": "from pymongo import MongoClient\nclient = MongoClient()\n",
    },
}


def enable_gate(root):
    store = Store(root)
    store.init()
    (store.dir / "config.yaml").write_text("tier0_gate: block\n")
    return store


# -- evaluate() unit level ----------------------------------------------------


def commitment(attrs):
    return Commitment(
        id="c-2026-07-13-0001",
        ts=datetime(2026, 7, 13, tzinfo=UTC),
        claim="The primary database is PostgreSQL 16.",
        kind=Kind.DECISION,
        scope=attrs,
        entitlement=Entitlement(source=EntitlementSource.USER_UTTERANCE),
    )


def test_first_conflicting_write_is_denied_then_retry_passes(tmp_path):
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    state = tmp_path / "tier0-gate.json"
    first = tier0_gate.evaluate("import pymongo", active, state)
    assert first is not None
    assert "BLOCKED" in first.reason and "c-2026-07-13-0001" in first.reason
    assert "retry" in first.reason  # the entitled path is spelled out
    # same (commitment, rival) pair again -> speed bump already consumed
    assert tier0_gate.evaluate("import pymongo", active, state) is None
    # alias of the same rival is the same pair (pymongo ~ mongodb)
    assert tier0_gate.evaluate("use mongodb here", active, state) is None


def test_distinct_rival_is_a_fresh_bump(tmp_path):
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    state = tmp_path / "tier0-gate.json"
    assert tier0_gate.evaluate("import pymongo", active, state) is not None
    assert tier0_gate.evaluate("import cassandra", active, state) is not None


def test_no_pinned_attr_never_denies(tmp_path):
    active = [commitment(["topic:persistence"])]  # no attr: pin
    assert tier0_gate.evaluate("import pymongo", active, tmp_path / "s.json") is None


def test_corrupt_state_fails_open_to_a_fresh_bump(tmp_path):
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    state = tmp_path / "tier0-gate.json"
    state.write_text("{not json")
    assert tier0_gate.evaluate("import pymongo", active, state) is not None
    assert json.loads(state.read_text())["denied"]  # rewritten valid


def test_wrong_shape_state_never_raises(tmp_path):
    # hooks must never break the agent: valid JSON of the wrong shape
    # (adversarial-review finding) fails open instead of raising
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    for weird in ("null", "[]", '"str"', '{"denied": null}', '{"denied": 3}'):
        state = tmp_path / "tier0-gate.json"
        state.write_text(weird)
        assert tier0_gate.evaluate("import pymongo", active, state) is not None


def test_all_rivals_recorded_on_one_deny(tmp_path):
    # exhaustive scan: content naming TWO rivals must consume both pairs at
    # once, or a fresh process could deny the retry on the sibling rival
    # (adversarial-review finding: hash-randomized set iteration)
    active = [commitment(["attr:caching.backend=redis"])]
    state = tmp_path / "tier0-gate.json"
    first = tier0_gate.evaluate("use memcached with valkey fallback", active, state)
    assert first is not None and len(first.warnings) == 2
    assert tier0_gate.evaluate("memcached only now", active, state) is None
    assert tier0_gate.evaluate("valkey only now", active, state) is None


def test_expired_bump_rearms(tmp_path, monkeypatch):
    # a pair consumed long ago must bump again — otherwise a user-REJECTED
    # change leaves that rival unguarded forever (reject-burn finding)
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    state = tmp_path / "tier0-gate.json"
    assert tier0_gate.evaluate("import pymongo", active, state) is not None
    assert tier0_gate.evaluate("import pymongo", active, state) is None  # within window
    real_time = tier0_gate.time.time
    monkeypatch.setattr(tier0_gate.time, "time",
                        lambda: real_time() + tier0_gate.REARM_SECONDS + 1)
    assert tier0_gate.evaluate("import pymongo", active, state) is not None


def test_legacy_list_state_is_understood(tmp_path):
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    state = tmp_path / "tier0-gate.json"
    state.write_text('{"denied": ["c-2026-07-13-0001:mongodb"]}')
    assert tier0_gate.evaluate("import pymongo", active, state) is None


# -- hook level (stdin/stdout contract) ----------------------------------------


def test_hook_denies_first_rival_write(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    enable_gate(tmp_path)
    out = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    assert spec["permissionDecision"] == "deny"
    assert "c-2026-07-08-0001" in spec["permissionDecisionReason"]
    # the deny is on the audit log
    assert any(e["op"] == "TIER0-GATE-DENY" for e in Store(tmp_path).log_entries())


def test_hook_lets_the_retry_pass(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    enable_gate(tmp_path)
    assert run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    retry = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    assert retry is None


def test_hook_is_a_noop_unless_opted_in(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    Store(tmp_path).init()  # no config.yaml, no env
    out = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    assert out is None


def test_env_var_enables_gate(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    Store(tmp_path).init()
    monkeypatch.setenv("SCOREKEEPER_TIER0_GATE", "block")
    out = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_aligned_write_is_never_denied(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    enable_gate(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "app/db.py", "content": "import psycopg\n"},
    }
    assert run_hook(monkeypatch, capsys, "pre-tool-use", payload) is None
