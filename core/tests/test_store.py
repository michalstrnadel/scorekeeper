"""Golden round-trip + rendering tests for the store."""

from datetime import UTC, datetime

from scorekeeper import Commitment, Entitlement, EntitlementSource, Kind, Status, Store, new_id


def make(cid: str, claim: str, **kw) -> Commitment:
    defaults = dict(
        id=cid,
        ts=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
        session="s-test",
        claim=claim,
        kind=Kind.DECISION,
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
        entitlement=Entitlement(
            source=EntitlementSource.USER_UTTERANCE, refs=["transcript:msg-1"]
        ),
    )
    defaults.update(kw)
    return Commitment(**defaults)


def test_roundtrip(tmp_path):
    store = Store(tmp_path)
    c = make("c-2026-07-08-0001", "Primary database is PostgreSQL 16.")
    store.save(c)
    loaded = store.load(c.id)
    assert loaded == c


def test_all_sorted_and_active(tmp_path):
    store = Store(tmp_path)
    store.save(make("c-2026-07-08-0002", "B"))
    store.save(make("c-2026-07-08-0001", "A"))
    store.save(
        make("c-2026-07-08-0003", "C", status=Status.SUPERSEDED, superseded_by="c-2026-07-08-0002")
    )
    assert [c.id for c in store.all()] == [
        "c-2026-07-08-0001",
        "c-2026-07-08-0002",
        "c-2026-07-08-0003",
    ]
    assert [c.claim for c in store.active()] == ["A", "B"]


def test_conflicted_stays_active(tmp_path):
    store = Store(tmp_path)
    store.save(make("c-2026-07-08-0001", "A", status=Status.CONFLICTED))
    assert [c.id for c in store.active()] == ["c-2026-07-08-0001"]


def test_scope_attrs_parsing():
    c = make("c-2026-07-08-0001", "x")
    assert c.scope_attrs == {"persistence.primary_db": "postgresql"}
    assert c.topics == {"persistence"}


def test_new_id_increments_globally():
    existing = ["c-2026-07-07-0001", "c-2026-07-07-0009"]
    nid = new_id(existing, now=datetime(2026, 7, 8, tzinfo=UTC))
    assert nid == "c-2026-07-08-0010"
    assert new_id([], now=datetime(2026, 7, 8, tzinfo=UTC)) == "c-2026-07-08-0001"


def test_log_roundtrip(tmp_path):
    store = Store(tmp_path)
    store.log("ASSERT", "c-2026-07-08-0001", "created")
    store.log("BRANCH-CONFLICT", "c-2026-07-08-0002", "collision", against="c-2026-07-08-0001")
    entries = store.log_entries()
    assert [e["op"] for e in entries] == ["ASSERT", "BRANCH-CONFLICT"]
    assert entries[1]["against"] == "c-2026-07-08-0001"


def test_digest_priority_and_budget(tmp_path):
    store = Store(tmp_path)
    store.save(make("c-2026-07-08-0001", "Normal decision"))
    store.save(
        make(
            "c-2026-07-08-0002",
            "Unbacked claim",
            kind=Kind.ASSERTION,
            entitlement=Entitlement(source=EntitlementSource.NONE),
        )
    )
    store.save(
        make(
            "c-2026-07-08-0003",
            "Conflicting choice",
            status=Status.CONFLICTED,
            incompatible_with=["c-2026-07-08-0001"],
        )
    )
    digest = store.render_digest()
    lines = digest.splitlines()
    assert "CONFLICT" in lines[1] and "c-2026-07-08-0003" in lines[1]
    assert "UNBACKED" in lines[2] and "c-2026-07-08-0002" in lines[2]
    assert "c-2026-07-08-0001" in lines[3]

    # budget: many commitments must truncate with a pointer, never exceed max
    for i in range(4, 80):
        store.save(make(f"c-2026-07-08-{i:04d}", f"Decision {i}"))
    digest = store.render_digest(max_lines=20)
    assert len(digest.splitlines()) <= 20
    assert "more — see" in digest


def test_digest_empty(tmp_path):
    assert Store(tmp_path).render_digest() == ""


def test_scoreboard_render(tmp_path):
    store = Store(tmp_path)
    store.save(make("c-2026-07-08-0001", "Primary database is PostgreSQL 16."))
    store.save(
        make(
            "c-2026-07-08-0002",
            "Old choice",
            status=Status.SUPERSEDED,
            superseded_by="c-2026-07-08-0001",
        )
    )
    store.write_scoreboard()
    text = store.scoreboard_path.read_text()
    assert "## Active commitments" in text
    assert "PostgreSQL 16" in text
    assert "→ c-2026-07-08-0001" in text


def test_write_lock_is_reentrant_per_instance(tmp_path):
    """apply() takes the lock itself; callers that pre-lock must nest freely
    (flock alone is not re-entrant across separate opens of the lock file)."""
    store = Store(tmp_path)
    with store.write_lock(), store.write_lock():  # inner would flock-block before the fix
        store.init()
    # released after the outer exit: a second Store instance can acquire non-blocking
    with Store(tmp_path).write_lock(blocking=False):
        pass


def test_write_lock_still_excludes_other_instances(tmp_path):
    """Re-entrancy is per instance only — real cross-writer exclusion stays."""
    import pytest

    store = Store(tmp_path)
    other = Store(tmp_path)
    with store.write_lock(), pytest.raises(BlockingIOError), other.write_lock(blocking=False):
        pass
