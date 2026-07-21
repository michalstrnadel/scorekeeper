"""Blocking Tier-0 gate (ADR-0007) — deny once, let the retry pass."""

import json
from datetime import UTC, datetime

import pytest
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


# -- audit 2026-07-14 regressions ------------------------------------------------


def test_wall_allows_the_edit_that_removes_the_rival(tmp_path, monkeypatch, capsys):
    """The remediating edit (rival in old_string, mention still in new) must pass —
    the gate once denied the very edit that fixed the drift."""
    seed_commitment(tmp_path)
    enable_gate(tmp_path, mode="block")
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "app/db.py",
            "old_string": "from pymongo import MongoClient\nclient = MongoClient()\n",
            "new_string": "# pymongo removed per commitment\nimport psycopg\n",
        },
    }
    assert run_hook(monkeypatch, capsys, "pre-tool-use", payload) is None


def test_wall_still_denies_a_newly_introduced_rival_in_an_edit(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    enable_gate(tmp_path, mode="block")
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "app/db.py",
            "old_string": "import psycopg\n",
            "new_string": "from pymongo import MongoClient\n",
        },
    }
    out = run_hook(monkeypatch, capsys, "pre-tool-use", payload)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_wall_exempts_documentation_files(tmp_path, monkeypatch, capsys):
    """Prose arguing ABOUT the rival ('evaluated and rejected') lives in docs;
    a hard deny there is pure FPR — the advisory channel still covers it."""
    seed_commitment(tmp_path)
    enable_gate(tmp_path, mode="block")
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "docs/adr/0003-db.md",
            "content": "MongoDB was evaluated and rejected (no transactions).",
        },
    }
    assert run_hook(monkeypatch, capsys, "pre-tool-use", payload) is None


def test_wall_gates_notebook_writes_via_new_source(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    enable_gate(tmp_path, mode="block")
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "NotebookEdit",
        "tool_input": {
            "notebook_path": "analysis.ipynb",
            "new_source": "from pymongo import MongoClient",
            "edit_mode": "replace",
        },
    }
    out = run_hook(monkeypatch, capsys, "pre-tool-use", payload)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bump_fails_open_when_state_cannot_be_saved(tmp_path):
    """If the deny state can't persist, the promised passing retry would be
    re-denied forever — so an unsaveable state must not deny at all."""
    c = commitment(["attr:persistence.primary_db=postgresql"])
    state = tmp_path / "tier0-gate.json"
    state.mkdir()  # os.replace onto a directory raises OSError
    decision = tier0_gate.evaluate("from pymongo import MongoClient", [c], state)
    assert decision is None


# -- scope wall (ADR-0008): entitlement-keyed write-scope gating -----------------


def scope_commitment(pins, cid="c-2026-07-19-0001", source=EntitlementSource.USER_UTTERANCE):
    return Commitment(
        id=cid,
        ts=datetime(2026, 7, 19, tzinfo=UTC),
        claim="The task's write scope is the app service only.",
        kind=Kind.DECISION,
        scope=pins,
        entitlement=Entitlement(source=source),
    )


def test_scope_wall_denies_out_of_scope_write(tmp_path):
    active = [scope_commitment(["topic:task-scope", "path:app/**"])]
    d = tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path)
    assert d is not None
    assert d.target == "legacy/util.py"
    assert "c-2026-07-19-0001" in d.reason and "path:app/**" in d.reason


def test_scope_wall_allows_in_scope_write(tmp_path):
    active = [scope_commitment(["path:app/**"])]
    assert tier0_gate.evaluate_scope("app/db.py", active, tmp_path) is None
    assert tier0_gate.evaluate_scope("app/sub/deep/x.py", active, tmp_path) is None


def test_scope_inert_without_path_pins(tmp_path):
    # active commitments but no path: pins -> the wall does not exist
    active = [commitment(["attr:persistence.primary_db=postgresql"])]
    assert tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path) is None


def test_scope_union_across_commitments(tmp_path):
    # grants accumulate: a file covered by the SECOND entitled grant passes
    active = [
        scope_commitment(["path:app/**"], cid="c-2026-07-19-0001"),
        scope_commitment(["path:legacy/util.py"], cid="c-2026-07-19-0002"),
    ]
    assert tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path) is None
    assert tier0_gate.evaluate_scope("legacy/other.py", active, tmp_path) is not None


def test_unentitled_pin_does_not_widen_scope(tmp_path):
    # the self-attestation exploit, scope edition: a source=none commitment
    # carrying path:** must not widen the agent's own write scope
    active = [
        scope_commitment(["path:app/**"], cid="c-2026-07-19-0001"),
        scope_commitment(["path:**"], cid="c-2026-07-19-0002",
                         source=EntitlementSource.NONE),
    ]
    assert tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path) is not None


def test_scope_wall_lifts_when_entitled_grant_lands(tmp_path):
    active = [scope_commitment(["path:app/**"])]
    assert tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path) is not None
    active.append(scope_commitment(["path:legacy/util.py"], cid="c-2026-07-19-0002"))
    assert tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path) is None


def test_scope_glob_semantics(tmp_path):
    active = [scope_commitment(["path:app/**", "path:README.md", "path:*.toml"])]
    # subtree rule: app/** covers nesting
    assert tier0_gate.evaluate_scope("app/a/b/c.py", active, tmp_path) is None
    # exact file
    assert tier0_gate.evaluate_scope("README.md", active, tmp_path) is None
    # documented fnmatch caveat, pinned: a bare * crosses '/'
    assert tier0_gate.evaluate_scope("deep/dir/x.toml", active, tmp_path) is None
    # trailing-slash form is the same subtree rule
    slash = [scope_commitment(["path:app/"])]
    assert tier0_gate.evaluate_scope("app/x.py", slash, tmp_path) is None
    assert tier0_gate.evaluate_scope("apps/x.py", slash, tmp_path) is not None


def test_scope_case_insensitive_match(tmp_path):
    # APFS/NTFS are case-insensitive: APP/Main.PY writes the same file
    active = [scope_commitment(["path:app/**"])]
    assert tier0_gate.evaluate_scope("APP/Main.PY", active, tmp_path) is None


def test_path_traversal_is_normalized(tmp_path):
    active = [scope_commitment(["path:app/**"])]
    # app/../legacy/x is legacy/x — the dodge must not read as in-scope
    assert tier0_gate.evaluate_scope("app/../legacy/util.py", active, tmp_path) is not None
    assert tier0_gate.evaluate_scope("./app/x.py", active, tmp_path) is None


def test_absolute_and_relative_targets_equivalent(tmp_path):
    active = [scope_commitment(["path:app/**"])]
    assert tier0_gate.evaluate_scope(str(tmp_path / "app" / "x.py"), active, tmp_path) is None
    assert (
        tier0_gate.evaluate_scope(str(tmp_path / "legacy" / "x.py"), active, tmp_path)
        is not None
    )


def test_target_outside_root_is_denied(tmp_path):
    # the board can only grant scope inside the project it governs
    active = [scope_commitment(["path:**"])]
    assert tier0_gate.evaluate_scope("../outside.py", active, tmp_path) is not None
    assert tier0_gate.evaluate_scope("/etc/passwd", active, tmp_path) is not None


def test_symlink_escape_is_denied(tmp_path):
    # GhostApproval evasion: a symlink inside the repo pointing outside must
    # not make the write look in-scope (resolved before matching)
    root = tmp_path / "repo"
    (root / "app").mkdir(parents=True)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "target.py").write_text("x = 1\n")
    try:
        (root / "app" / "link.py").symlink_to(outside / "target.py")
        (root / "vendored").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")
    active = [scope_commitment(["path:app/**", "path:vendored/**"])]
    assert tier0_gate.evaluate_scope("app/link.py", active, root) is not None
    assert tier0_gate.evaluate_scope("vendored/target.py", active, root) is not None


def test_malformed_pin_is_skipped_never_raises(tmp_path):
    # a bad pin must not crash the hook — and must not grant anything either
    active = [scope_commitment(["path:[", "path:app/**"])]
    assert tier0_gate.evaluate_scope("app/x.py", active, tmp_path) is None
    assert tier0_gate.evaluate_scope("legacy/x.py", active, tmp_path) is not None


def test_scope_reason_teaches_the_grant_path(tmp_path):
    active = [scope_commitment(["path:app/**"])]
    d = tier0_gate.evaluate_scope("legacy/util.py", active, tmp_path)
    assert "say-so cannot lift it" in d.reason
    assert "surface the extra change" in d.reason          # branch (a)
    assert "supersede" in d.reason and "path:" in d.reason  # branch (b)
    assert "audited" in d.reason


# -- scope wall, hook level ------------------------------------------------------


LEGACY_EDIT = {
    "tool_name": "Write",
    "tool_input": {"file_path": "legacy/util.py", "content": "def helper():\n    pass\n"},
}


def seed_scope(root, mode="block"):
    seed_commitment(root, claim="The task's write scope is the app service only.",
                    attrs=["topic:task-scope", "path:app/**", "path:tests/**"])
    return enable_gate(root, mode=mode)


def test_hook_scope_denies_and_logs(tmp_path, monkeypatch, capsys):
    seed_scope(tmp_path)
    out = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **LEGACY_EDIT})
    spec = out["hookSpecificOutput"]
    assert spec["permissionDecision"] == "deny"
    assert "legacy/util.py" in spec["permissionDecisionReason"]
    assert any(e["op"] == "TIER0-SCOPE-DENY" for e in Store(tmp_path).log_entries())
    # the wall: an identical fresh attempt is still denied
    again = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **LEGACY_EDIT})
    assert again["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_hook_scope_allows_in_scope_write(tmp_path, monkeypatch, capsys):
    seed_scope(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "app/db.py", "content": "import psycopg\n"},
    }
    assert run_hook(monkeypatch, capsys, "pre-tool-use", payload) is None


def test_docs_are_not_scope_exempt(tmp_path, monkeypatch, capsys):
    # the .md exemption is a claims-content concern; a drive-by README edit
    # outside the entitled scope is still barging (ADR-0008 stance)
    seed_scope(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "docs/notes.md", "content": "drive-by cleanup"},
    }
    out = run_hook(monkeypatch, capsys, "pre-tool-use", payload)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_notebook_path_is_scope_gated(tmp_path, monkeypatch, capsys):
    seed_scope(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "NotebookEdit",
        "tool_input": {"notebook_path": "analysis.ipynb", "new_source": "x = 1"},
    }
    out = run_hook(monkeypatch, capsys, "pre-tool-use", payload)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_missing_target_falls_through_to_content_gate(tmp_path, monkeypatch, capsys):
    # a payload with no file_path/notebook_path cannot be scope-gated; the
    # claims gate still sees the content
    seed_scope(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"content": "def helper():\n    pass\n"},
    }
    assert run_hook(monkeypatch, capsys, "pre-tool-use", payload) is None


def test_scope_active_under_bump_mode_too(tmp_path, monkeypatch, capsys):
    # scope is wall-only even when the claims gate runs as a bump: the
    # instructed-retry channel was already exploited on claims
    seed_scope(tmp_path, mode="bump")
    assert run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **LEGACY_EDIT})
    again = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **LEGACY_EDIT})
    assert again["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_scope_kill_switch_env_and_config(tmp_path, monkeypatch, capsys):
    seed_scope(tmp_path)
    monkeypatch.setenv("SCOREKEEPER_SCOPE_GATE", "off")
    assert run_hook(monkeypatch, capsys, "pre-tool-use",
                    {"cwd": str(tmp_path), **LEGACY_EDIT}) is None
    monkeypatch.delenv("SCOREKEEPER_SCOPE_GATE")
    store = Store(tmp_path)
    (store.dir / "config.yaml").write_text("tier0_gate: block\nscope_gate: off\n")
    assert run_hook(monkeypatch, capsys, "pre-tool-use",
                    {"cwd": str(tmp_path), **LEGACY_EDIT}) is None
    # force-enable: scope wall alone, claims gate off
    (store.dir / "config.yaml").write_text("scope_gate: block\n")
    out = run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **LEGACY_EDIT})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_hook_scope_wall_lifts_on_entitled_grant(tmp_path, monkeypatch, capsys):
    seed_scope(tmp_path)
    assert run_hook(monkeypatch, capsys, "pre-tool-use", {"cwd": str(tmp_path), **LEGACY_EDIT})
    # the grant is a SECOND record — the union widens, the original pin stays
    Store(tmp_path).save(
        scope_commitment(["topic:task-scope", "path:legacy/util.py"],
                         cid="c-2026-07-19-0002")
    )
    assert run_hook(monkeypatch, capsys, "pre-tool-use",
                    {"cwd": str(tmp_path), **LEGACY_EDIT}) is None
