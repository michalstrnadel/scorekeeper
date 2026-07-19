"""Hook handler tests — stdin/stdout contract, transcript parsing, loop guard."""

import json
from datetime import UTC, datetime

import pytest

import scorekeeper.cli as cli_module
from scorekeeper import Commitment, Entitlement, EntitlementSource, Kind, Store
from scorekeeper.backends import BackendError
from scorekeeper.cli import main
from scorekeeper.detect import tier0_content
from scorekeeper.transcript import read_last_turn


def run_hook(monkeypatch, capsys, event: str, payload: dict) -> dict | None:
    monkeypatch.setattr("sys.stdin", FakeStdin(json.dumps(payload)))
    assert main(["hook", event]) == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else None


class FakeStdin:
    def __init__(self, text: str):
        self._text = text

    def read(self) -> str:
        return self._text


def seed_commitment(root, claim="The primary database is PostgreSQL 16.", attrs=None):
    store = Store(root)
    c = Commitment(
        id="c-2026-07-08-0001",
        ts=datetime(2026, 7, 8, tzinfo=UTC),
        claim=claim,
        kind=Kind.DECISION,
        scope=attrs or ["topic:persistence", "attr:persistence.primary_db=postgresql"],
        entitlement=Entitlement(source=EntitlementSource.USER_UTTERANCE),
    )
    store.save(c)
    return store


# -- SessionStart -----------------------------------------------------------------


def test_session_start_injects_digest(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    out = run_hook(monkeypatch, capsys, "session-start", {"cwd": str(tmp_path)})
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "PostgreSQL 16" in ctx and "ACTIVE COMMITMENTS" in ctx


def test_session_start_silent_when_empty(tmp_path, monkeypatch, capsys):
    out = run_hook(monkeypatch, capsys, "session-start", {"cwd": str(tmp_path)})
    assert out is None


# -- PostToolUse (tier0 content) ----------------------------------------------------


def test_post_tool_use_flags_rival(tmp_path, monkeypatch, capsys):
    store = seed_commitment(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "app/feed.py",
            "content": "import pymongo\nclient = pymongo.MongoClient(...)",
        },
    }
    out = run_hook(monkeypatch, capsys, "post-tool-use", payload)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "SCOREKEEPER WARNING" in ctx and "persistence.primary_db=postgresql" in ctx
    assert any(e["op"] == "TIER0-CONTENT-WARNING" for e in store.log_entries())


def test_post_tool_use_silent_on_aligned_content(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_input": {"file_path": "app/db.py", "content": "import psycopg\n# postgres pool"},
    }
    assert run_hook(monkeypatch, capsys, "post-tool-use", payload) is None


def test_post_tool_use_scope_warning_out_of_scope(tmp_path, monkeypatch, capsys):
    """Advisory scope twin (ADR-0008): a LANDED out-of-scope write warns and
    logs regardless of gate mode — the audit floor under the wall."""
    store = seed_commitment(
        tmp_path, claim="The task's write scope is the app service only.",
        attrs=["topic:task-scope", "path:app/**"],
    )
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "legacy/util.py", "content": "def helper(): pass"},
    }
    out = run_hook(monkeypatch, capsys, "post-tool-use", payload)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "outside the task's entitled write scope" in ctx and "legacy/util.py" in ctx
    assert any(e["op"] == "TIER0-SCOPE-WARNING" for e in store.log_entries())


def test_post_tool_use_scope_silent_in_scope(tmp_path, monkeypatch, capsys):
    seed_commitment(
        tmp_path, claim="The task's write scope is the app service only.",
        attrs=["topic:task-scope", "path:app/**"],
    )
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "app/db.py", "content": "x = 1\n"},
    }
    assert run_hook(monkeypatch, capsys, "post-tool-use", payload) is None


# -- transcript parsing --------------------------------------------------------------


def write_transcript(path, entries):
    path.write_text("\n".join(json.dumps(e) for e in entries))


def entry(role, blocks):
    return {"type": role, "message": {"role": role, "content": blocks}}


def test_read_last_turn(tmp_path):
    t = tmp_path / "t.jsonl"
    write_transcript(
        t,
        [
            entry("user", [{"type": "text", "text": "old turn"}]),
            entry("assistant", [{"type": "text", "text": "old reply"}]),
            entry("user", [{"type": "text", "text": "use postgres 16"}]),
            entry(
                "assistant",
                [
                    {"type": "text", "text": "Setting up Postgres."},
                    {"type": "tool_use", "name": "Write", "input": {"file_path": "app/db.py"}},
                ],
            ),
            entry("user", [{"type": "tool_result", "content": "ok"}]),
            entry("assistant", [{"type": "text", "text": "Done — connection module created."}]),
        ],
    )
    turn = read_last_turn(t)
    assert turn.user_text == "use postgres 16"
    assert "Setting up Postgres." in turn.assistant_text
    assert "Done — connection module created." in turn.assistant_text
    assert turn.tools_used == ["Write(app/db.py)"]


def test_read_last_turn_tolerates_garbage(tmp_path):
    t = tmp_path / "t.jsonl"
    t.write_text('not json\n{"type": "system"}\n')
    assert read_last_turn(t).empty


# -- Stop hook ------------------------------------------------------------------------


def test_stop_loop_guard(tmp_path, monkeypatch, capsys):
    out = run_hook(
        monkeypatch, capsys, "stop", {"cwd": str(tmp_path), "stop_hook_active": True}
    )
    assert out is None


def test_stop_no_backend_logs_and_exits_zero(tmp_path, monkeypatch, capsys):
    t = tmp_path / "t.jsonl"
    write_transcript(
        t,
        [
            entry("user", [{"type": "text", "text": "use postgres"}]),
            entry("assistant", [{"type": "text", "text": "ok, postgres it is"}]),
        ],
    )
    def no_backend(root):
        raise BackendError("none")

    monkeypatch.setattr("scorekeeper.cli.detect_backend", no_backend)
    out = run_hook(
        monkeypatch, capsys, "stop", {"cwd": str(tmp_path), "transcript_path": str(t)}
    )
    assert out is None
    assert any(e["op"] == "ERROR" for e in Store(tmp_path).log_entries())


def test_stop_extracts_and_blocks_on_conflict(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    t = tmp_path / "t.jsonl"
    write_transcript(
        t,
        [
            entry("user", [{"type": "text", "text": "implement the feed per the note"}]),
            entry("assistant", [{"type": "text", "text": "Using MongoDB for the feed."}]),
        ],
    )

    class FakeBackend:
        name = "fake"

        def complete(self, system, user):
            if "commitment extractor" in system:
                return json.dumps(
                    {
                        "commitments": [
                            {
                                "claim": "Activity feed storage uses MongoDB.",
                                "kind": "decision",
                                "scope": [
                                    "topic:persistence",
                                    "attr:persistence.primary_db=mongodb",
                                ],
                                "entitlement": {"source": "prior_inference", "note": "note"},
                            }
                        ]
                    }
                )
            return json.dumps({"verdicts": []})

    monkeypatch.setattr("scorekeeper.cli.detect_backend", lambda root: FakeBackend())
    out = run_hook(
        monkeypatch, capsys, "stop", {"cwd": str(tmp_path), "transcript_path": str(t)}
    )
    assert out["decision"] == "block"
    assert "COMMITMENT CONFLICT" in out["reason"]
    assert "PostgreSQL 16" in out["reason"]


# -- async extraction (ADR-0006) ------------------------------------------------------


class ConflictBackend:
    """Extractor stub that produces a MongoDB drift commitment."""

    name = "fake"

    def complete(self, system, user):
        if "commitment extractor" in system:
            return json.dumps(
                {
                    "commitments": [
                        {
                            "claim": "Activity feed storage uses MongoDB.",
                            "kind": "decision",
                            "scope": [
                                "topic:persistence",
                                "attr:persistence.primary_db=mongodb",
                            ],
                            "entitlement": {"source": "prior_inference", "note": "note"},
                        }
                    ]
                }
            )
        return json.dumps({"verdicts": []})


def drift_transcript(tmp_path):
    t = tmp_path / "t.jsonl"
    write_transcript(
        t,
        [
            entry("user", [{"type": "text", "text": "implement the feed per the note"}]),
            entry("assistant", [{"type": "text", "text": "Using MongoDB for the feed."}]),
        ],
    )
    return t


def test_stop_async_spawns_worker_and_returns_silent(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    t = drift_transcript(tmp_path)
    spawned = []
    monkeypatch.setenv("SCOREKEEPER_EXTRACT", "async")
    monkeypatch.setattr(
        "scorekeeper.cli.subprocess.Popen", lambda *a, **kw: spawned.append(a[0])
    )
    out = run_hook(
        monkeypatch, capsys, "stop", {"cwd": str(tmp_path), "transcript_path": str(t)}
    )
    assert out is None  # never blocks in async mode
    assert len(spawned) == 1 and spawned[0][-2] == "worker"
    payloads = list((Store(tmp_path).dir / "worker").glob("payload-*.json"))
    assert len(payloads) == 1
    assert json.loads(payloads[0].read_text())["transcript_path"] == str(t)


def test_worker_writes_pending_and_prompt_submit_drains(tmp_path, monkeypatch, capsys):
    store = seed_commitment(tmp_path)
    t = drift_transcript(tmp_path)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps({"cwd": str(tmp_path), "transcript_path": str(t), "session_id": "s1"})
    )
    monkeypatch.setattr("scorekeeper.cli.detect_backend", lambda root: ConflictBackend())
    assert main(["worker", str(payload_path)]) == 0
    pending = store.dir / "pending-findings.md"
    assert "COMMITMENT CONFLICT" in pending.read_text()
    assert not payload_path.exists()  # consumed

    out = run_hook(monkeypatch, capsys, "user-prompt-submit", {"cwd": str(tmp_path)})
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "COMMITMENT CONFLICT" in ctx and "PostgreSQL 16" in ctx
    assert not pending.exists()  # drained exactly once


def test_user_prompt_submit_silent_without_pending(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    assert run_hook(monkeypatch, capsys, "user-prompt-submit", {"cwd": str(tmp_path)}) is None


# -- PreCompact -------------------------------------------------------------------------


def test_pre_compact_backs_up(tmp_path, monkeypatch, capsys):
    store = seed_commitment(tmp_path)
    run_hook(monkeypatch, capsys, "pre-compact", {"cwd": str(tmp_path)})
    backups = list((store.dir / "backups").glob("scoreboard-*.md"))
    assert len(backups) == 1
    assert "PostgreSQL 16" in backups[0].read_text()


# -- crash safety -----------------------------------------------------------------------


def test_hook_never_raises(tmp_path, monkeypatch, capsys):
    def boom(payload):
        raise RuntimeError("boom")

    monkeypatch.setitem(cli_module.HOOKS, "session-start", boom)
    monkeypatch.setattr("sys.stdin", FakeStdin(json.dumps({"cwd": str(tmp_path)})))
    assert main(["hook", "session-start"]) == 0
    assert "error" in capsys.readouterr().err


# -- tier0_content unit ---------------------------------------------------------------


def test_tier0_content_scan():
    c = Commitment(
        id="c-1",
        ts=datetime(2026, 7, 8, tzinfo=UTC),
        claim="Caching uses Redis.",
        kind=Kind.DECISION,
        scope=["attr:caching.backend=redis"],
    )
    hits = tier0_content.scan("import memcached  # swap cache", [c])
    assert len(hits) == 1 and hits[0].rival_found == "memcached"
    assert tier0_content.scan("redis.Redis(host=...)", [c]) == []
    assert tier0_content.scan("unrelated text", [c]) == []


def test_tier0_content_alias():
    c = Commitment(
        id="c-1",
        ts=datetime(2026, 7, 8, tzinfo=UTC),
        claim="Primary DB is Postgres.",
        kind=Kind.DECISION,
        scope=["attr:persistence.primary_db=postgres"],
    )
    hits = tier0_content.scan("from pymongo import MongoClient", [c])
    assert len(hits) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-q"])


# -- audit 2026-07-14 regressions ------------------------------------------------


def test_bash_post_hook_audits_shell_rivals_log_only(tmp_path, monkeypatch, capsys):
    """Shell writes are AUDITED (the wall's deterrent sentence must be true)
    but never warned — `grep mongodb` is not drift."""
    seed_commitment(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "cat > db.py <<EOF\nfrom pymongo import MongoClient\nEOF"},
    }
    out = run_hook(monkeypatch, capsys, "post-tool-use", payload)
    assert out is None
    assert any(e["op"] == "TIER0-SHELL-AUDIT" for e in Store(tmp_path).log_entries())


def test_post_hook_silent_when_edit_removes_the_rival(tmp_path, monkeypatch, capsys):
    """old_string is a suppressor, never a trigger: fixing drift must not warn."""
    seed_commitment(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "app/db.py",
            "old_string": "from pymongo import MongoClient",
            "new_string": "import psycopg",
        },
    }
    assert run_hook(monkeypatch, capsys, "post-tool-use", payload) is None


def test_post_hook_scans_notebook_new_source(tmp_path, monkeypatch, capsys):
    seed_commitment(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "NotebookEdit",
        "tool_input": {
            "notebook_path": "nb.ipynb",
            "new_source": "from pymongo import MongoClient",
        },
    }
    out = run_hook(monkeypatch, capsys, "post-tool-use", payload)
    assert "pymongo" in out["hookSpecificOutput"]["additionalContext"]


def test_drain_skips_while_worker_holds_the_lock(tmp_path, monkeypatch, capsys):
    """Unlocked read+unlink deleted findings a worker appended in between;
    the drain now takes the worker lock, non-blocking (skip, never stall)."""
    import fcntl

    store = Store(tmp_path)
    store.init()
    (store.dir / "pending-findings.md").write_text("COMMITMENT CONFLICT: X\n")
    with (store.dir / "worker.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        out = run_hook(monkeypatch, capsys, "user-prompt-submit", {"cwd": str(tmp_path)})
        assert out is None  # skipped, not stalled
        assert (store.dir / "pending-findings.md").exists()  # nothing lost
    out = run_hook(monkeypatch, capsys, "user-prompt-submit", {"cwd": str(tmp_path)})
    assert "COMMITMENT CONFLICT: X" in out["hookSpecificOutput"]["additionalContext"]


def test_pre_compact_skips_empty_store_and_preserves_hand_scoreboard(
    tmp_path, monkeypatch, capsys
):
    """Regression: an empty store (records dir exists, zero c-*.yaml) with a
    hand-maintained scoreboard.md — this repo's own pre-MVP board — was
    clobbered by the pre-compact regeneration."""
    store = Store(tmp_path)
    store.init()
    store.scoreboard_path.write_text("# Hand-maintained board\n")
    run_hook(monkeypatch, capsys, "pre-compact", {"cwd": str(tmp_path)})
    assert store.scoreboard_path.read_text() == "# Hand-maintained board\n"
    assert not (store.dir / "backups").exists()


def test_pre_compact_skips_when_writer_holds_the_lock(tmp_path, monkeypatch, capsys):
    """A backup snapshotted mid-apply() could persist a half-applied transition;
    the hook must skip rather than block or snapshot."""
    store = seed_commitment(tmp_path)
    with Store(tmp_path).write_lock():
        run_hook(monkeypatch, capsys, "pre-compact", {"cwd": str(tmp_path)})
    assert not list((store.dir / "backups").glob("scoreboard-*.md"))


def test_hook_error_handler_never_creates_store(tmp_path, monkeypatch, capsys):
    """The catch-all audit log is best-effort — it must not materialize
    .scorekeeper/ in repos the user never initialized."""
    monkeypatch.setattr(
        cli_module, "HOOKS", {**cli_module.HOOKS, "stop": _raise_for_test}
    )
    monkeypatch.setattr("sys.stdin", FakeStdin(json.dumps({"cwd": str(tmp_path)})))
    assert main(["hook", "stop"]) == 0
    assert not (tmp_path / ".scorekeeper").exists()


def _raise_for_test(payload):
    raise RuntimeError("boom")


def test_extract_mode_precedence(tmp_path, monkeypatch):
    """SCOREKEEPER_EXTRACT > config extract: > SCOREKEEPER_EXTRACT_DEFAULT > sync.
    Regression: the plugin's hooks.json used to inject SCOREKEEPER_EXTRACT
    itself, making the config key dead under the plugin."""
    from scorekeeper.cli import _extract_mode

    for var in ("SCOREKEEPER_EXTRACT", "SCOREKEEPER_EXTRACT_DEFAULT"):
        monkeypatch.delenv(var, raising=False)
    assert _extract_mode(tmp_path) == "sync"  # bare default

    monkeypatch.setenv("SCOREKEEPER_EXTRACT_DEFAULT", "async")  # plugin surface default
    assert _extract_mode(tmp_path) == "async"

    store = Store(tmp_path)
    store.init()
    (store.dir / "config.yaml").write_text("extract: sync\n")  # config beats surface default
    assert _extract_mode(tmp_path) == "sync"

    monkeypatch.setenv("SCOREKEEPER_EXTRACT", "async")  # user env beats everything
    assert _extract_mode(tmp_path) == "async"
