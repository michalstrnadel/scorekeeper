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


def enable_gate(root, mode="bump"):
    store = Store(root)
    store.init()
    (store.dir / "config.yaml").write_text(f"tier0_gate: {mode}\n")
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


# -- gate v2: the wall (board-adjudicated pass) --------------------------------


def test_wall_denies_repeatedly_while_commitment_active():
    # v1's exploited escape: retrying must NOT lift the v2 wall
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    for _ in range(3):
        d = tier0_gate.evaluate_wall("import pymongo", active)
        assert d is not None
        assert "say-so cannot lift it" in d.reason


def test_wall_lifts_when_board_records_the_supersede():
    # the pass condition is the BOARD changing: superseded commitments drop
    # out of store.active(), so the wall goes quiet without any gate state
    from scorekeeper.model import Status

    c = commitment(["attr:persistence.primary_db=postgresql"])
    assert tier0_gate.evaluate_wall("import pymongo", [c]) is not None
    c.status = Status.SUPERSEDED
    active = [x for x in [c] if x.status in (Status.ACTIVE, Status.CONFLICTED)]
    assert tier0_gate.evaluate_wall("import pymongo", active) is None


def test_camouflaged_driver_only_drift_is_caught():
    # live miss 2026-07-14: agent wrote `from pymemcache.client.hash import
    # HashClient` with a docstring claiming "backed by Redis" — the rival's
    # product name appeared ZERO times, only the driver's. Driver tokens are
    # first-class lexicon members now.
    active = [commitment(["attr:caching.backend=redis"])]
    d = tier0_gate.evaluate_wall(
        '"""Event cache backed by Redis."""\nfrom pymemcache.client.hash import HashClient\n',
        active,
    )
    assert d is not None and d.warnings[0].rival_found == "pymemcache"


def test_wall_reason_spells_out_both_branches():
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    d = tier0_gate.evaluate_wall("import pymongo", active)
    assert "surface the conflict" in d.reason  # branch (a)
    assert "supersede" in d.reason  # branch (b): record it on the board


def test_hook_mode_block_is_wall_and_bump_is_speed_bump(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    store = Store(tmp_path)
    store.init()
    (store.dir / "config.yaml").write_text("tier0_gate: block\n")
    # wall: second identical attempt is STILL denied
    assert run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    again = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    assert again["hookSpecificOutput"]["permissionDecision"] == "deny"
    # bump: deny once, retry passes
    (store.dir / "config.yaml").write_text("tier0_gate: bump\n")
    assert run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    retry = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **MONGO_EDIT})
    assert retry is None


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
