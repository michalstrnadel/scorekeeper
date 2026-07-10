"""Operator tests — the SUPERSEDE vs BRANCH-CONFLICT boundary, mirroring scenarios 01/04a/04b/05."""

import json

from scorekeeper import Status, Store
from scorekeeper.extract import ExtractedCommitment
from scorekeeper.operators import apply


class VerdictBackend:
    """Tier-1 stub: returns configured verdicts for every judged pair."""

    name = "stub"

    def __init__(self, verdict: str = "compatible", rationale: str = "stub"):
        self.verdict = verdict
        self.rationale = rationale
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        ids = [
            line.split()[2].rstrip(":")
            for line in user.splitlines()
            if line.startswith("- id ")
        ]
        verdicts = [
            {"id": i, "verdict": self.verdict, "rationale": self.rationale} for i in ids
        ]
        return json.dumps({"verdicts": verdicts})


def ext(claim: str, kind: str = "decision", scope=None, source: str = "user_utterance"):
    return ExtractedCommitment(
        claim=claim,
        kind=kind,
        scope=scope or [],
        entitlement={"source": source, "note": "t"},
    )


POSTGRES = ext(
    "The primary database is PostgreSQL 16.",
    scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
)


def test_plain_assert(tmp_path):
    store = Store(tmp_path)
    result = apply(store, [POSTGRES])
    assert len(result.asserted) == 1
    assert store.active()[0].claim.startswith("The primary database")
    assert store.scoreboard_path.exists()


def test_scenario01_unentitled_drift_conflicts(tmp_path):
    """Agent drifts to MongoDB on its own -> BRANCH-CONFLICT, nothing destroyed."""
    store = Store(tmp_path)
    apply(store, [POSTGRES])
    mongo = ext(
        "Activity feed storage uses MongoDB.",
        scope=["topic:persistence", "attr:persistence.primary_db=mongodb"],
        source="prior_inference",
    )
    result = apply(store, [mongo])
    assert len(result.conflicts) == 1
    assert result.conflicts[0].reason.startswith("tier0")
    both = store.active()
    assert all(c.status == Status.CONFLICTED for c in both)
    assert both[0].incompatible_with == [both[1].id]
    assert both[1].incompatible_with == [both[0].id]


def test_scenario04a_entitled_revision_supersedes(tmp_path):
    """User revokes Redis -> SUPERSEDE with bidirectional chain, no conflict."""
    store = Store(tmp_path)
    redis = ext("Caching uses Redis.", scope=["topic:caching", "attr:caching.backend=redis"])
    apply(store, [redis])
    lru = ext(
        "Caching uses an in-process LRU.",
        scope=["topic:caching", "attr:caching.backend=in_process_lru"],
        source="user_utterance",
    )
    result = apply(store, [lru])
    assert result.conflicts == []
    assert len(result.superseded) == 1
    old_id, new_id_ = result.superseded[0]
    old, new = store.load(old_id), store.load(new_id_)
    assert old.status == Status.SUPERSEDED and old.superseded_by == new.id
    assert new.supersedes == old.id and new.status == Status.ACTIVE
    assert [c.id for c in store.active()] == [new.id]


def test_scenario04b_tier1_drift_conflicts(tmp_path):
    """No attr collision, but Tier-1 finds material incompatibility; agent not entitled."""
    store = Store(tmp_path)
    apply(store, [ext("Caching uses Redis in production.", scope=["topic:caching"])])
    drift = ext(
        "All caching is in-process; Redis dependency removed.",
        scope=["topic:caching"],
        source="prior_inference",
    )
    backend = VerdictBackend("incompatible", "removes the production backend")
    result = apply(store, [drift], backend=backend)
    assert backend.calls == 1
    assert len(result.conflicts) == 1
    assert "tier1" in result.conflicts[0].reason


def test_tier1_compatible_no_conflict(tmp_path):
    store = Store(tmp_path)
    apply(store, [ext("Caching uses Redis in production.", scope=["topic:caching"])])
    dev = ext(
        "Local development uses an in-memory cache fallback.",
        scope=["topic:caching", "topic:environments"],
    )
    result = apply(store, [dev], backend=VerdictBackend("compatible"))
    assert result.conflicts == [] and result.superseded == []
    assert len(store.active()) == 2


def test_refine_keeps_chain(tmp_path):
    store = Store(tmp_path)
    apply(store, [POSTGRES])
    pinned = ext(
        "The primary database is PostgreSQL 16.3 (pinned).",
        scope=["topic:persistence"],
        source="user_utterance",
    )
    result = apply(store, [pinned], backend=VerdictBackend("refines"))
    assert len(result.refined) == 1
    old_id, new_id_ = result.refined[0]
    assert store.load(old_id).status == Status.REFINED
    assert store.load(old_id).superseded_by == new_id_


def test_f2_entitled_collision_compatible_coexists(tmp_path):
    """Phase-0 finding F2: an entitled dev-env change colliding on the attr key must
    NOT supersede the production commitment when Tier-1 says they coexist."""
    store = Store(tmp_path)
    redis = ext("Caching uses Redis.", scope=["topic:caching", "attr:caching.backend=redis"])
    apply(store, [redis])
    dev = ext(
        "Development environment uses an in-memory cache.",
        scope=["topic:caching", "attr:caching.backend=memory"],
        source="user_utterance",
    )
    backend = VerdictBackend("compatible", "different environments")
    result = apply(store, [dev], backend=backend)
    assert backend.calls == 1
    assert result.superseded == [] and result.conflicts == []
    assert len(store.active()) == 2
    assert any(e["op"] == "COEXIST" for e in store.log_entries())


def test_f2_entitled_collision_incompatible_still_supersedes(tmp_path):
    """04a behavior preserved with a backend: a confirmed replacement supersedes."""
    store = Store(tmp_path)
    redis = ext("Caching uses Redis.", scope=["topic:caching", "attr:caching.backend=redis"])
    apply(store, [redis])
    lru = ext(
        "Caching uses an in-process LRU.",
        scope=["topic:caching", "attr:caching.backend=in_process_lru"],
        source="user_utterance",
    )
    result = apply(store, [lru], backend=VerdictBackend("incompatible", "replaces the backend"))
    assert len(result.superseded) == 1 and result.conflicts == []
    assert len(store.active()) == 1


def test_f2_entitled_collision_refines(tmp_path):
    store = Store(tmp_path)
    apply(store, [POSTGRES])
    pinned = ext(
        "The primary database is PostgreSQL 16.3.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql_16.3"],
        source="user_utterance",
    )
    result = apply(store, [pinned], backend=VerdictBackend("refines"))
    assert len(result.refined) == 1 and result.superseded == []


def test_f2_unentitled_collision_still_deterministic_conflict(tmp_path):
    """Drift stays a zero-LLM hard catch — Tier-1 must NOT be consulted for it."""
    store = Store(tmp_path)
    apply(store, [POSTGRES])
    mongo = ext(
        "Activity feed storage uses MongoDB.",
        scope=["topic:persistence", "attr:persistence.primary_db=mongodb"],
        source="prior_inference",
    )
    backend = VerdictBackend("compatible")
    result = apply(store, [mongo], backend=backend)
    assert len(result.conflicts) == 1
    # the only tier1 call allowed is the general candidate pass, not a collision waiver
    assert not any(e["op"] == "COEXIST" for e in store.log_entries())


def test_scenario05_challenge_unbacked(tmp_path):
    store = Store(tmp_path)
    halluc = ext(
        "httpmini supports automatic retries with jitter.",
        kind="assertion",
        scope=["topic:vendored-lib"],
        source="none",
    )
    result = apply(store, [halluc])
    assert result.challenges == result.asserted
    assert any(e["op"] == "CHALLENGE" for e in store.log_entries())


def test_duplicate_claim_supports(tmp_path):
    store = Store(tmp_path)
    apply(store, [POSTGRES], refs=["transcript:msg-1"])
    result = apply(store, [POSTGRES], refs=["transcript:msg-9"])
    assert result.asserted == [] and len(result.supported) == 1
    only = store.active()[0]
    assert "transcript:msg-9" in only.entitlement.refs
    assert len(store.all()) == 1


def test_tier0_agreement_supports(tmp_path):
    store = Store(tmp_path)
    apply(store, [POSTGRES])
    same_attr = ext(
        "User records live in PostgreSQL.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    )
    result = apply(store, [same_attr])
    assert result.conflicts == []
    assert len(result.supported) == 1
    assert len(store.active()) == 2
