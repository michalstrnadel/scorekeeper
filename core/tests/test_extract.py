"""Extractor plumbing tests — validation gate, repair retry, failure modes. No network."""

from datetime import UTC, datetime

import pytest

from scorekeeper.backends.base import BackendError
from scorekeeper.extract import (
    ExtractedCommitment,
    build_turn_text,
    extract_commitments,
    suspect_note,
)
from scorekeeper.model import Commitment, EntitlementSource, Kind


class SeqBackend:
    """Returns queued responses; records prompts it was given."""

    name = "seq"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, system: str, user: str) -> str:
        self.prompts.append(user)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


GOOD = (
    '{"commitments": [{"claim": "The primary database is PostgreSQL 16.",'
    ' "kind": "decision",'
    ' "scope": ["topic:persistence", "attr:persistence.primary_db=postgresql"],'
    ' "entitlement": {"source": "user_utterance", "note": "user chose it"},'
    ' "consequences": ["ORM must support PostgreSQL"]}]}'
)


def test_happy_path():
    out = extract_commitments(SeqBackend(GOOD), "USER: use postgres 16")
    assert len(out) == 1
    c = out[0]
    assert c.kind == Kind.DECISION
    assert c.entitlement.source == EntitlementSource.USER_UTTERANCE
    assert "attr:persistence.primary_db=postgresql" in c.scope


def test_empty_is_normal():
    out = extract_commitments(SeqBackend('{"commitments": []}'), "USER: thanks!")
    assert out == []


def test_repair_retry_recovers():
    backend = SeqBackend("I think the commitments here are...", GOOD)
    out = extract_commitments(backend, "turn")
    assert len(out) == 1
    assert "previous reply was invalid" in backend.prompts[1]


def test_repair_retry_gives_up_and_reports():
    errors = []
    backend = SeqBackend("garbage", "more garbage")
    out = extract_commitments(backend, "turn", on_error=errors.append)
    assert out == []
    assert len(errors) == 1


def test_invalid_scope_rejected_then_repaired():
    bad_scope = GOOD.replace('"topic:persistence"', '"persistence"')
    backend = SeqBackend(bad_scope, GOOD)
    out = extract_commitments(backend, "turn")
    assert len(out) == 1


def test_backend_error_returns_empty():
    errors = []
    backend = SeqBackend(BackendError("connection refused"))
    out = extract_commitments(backend, "turn", on_error=errors.append)
    assert out == []
    assert isinstance(errors[0], BackendError)


def test_digest_prepended():
    backend = SeqBackend('{"commitments": []}')
    extract_commitments(backend, "USER: hi", digest="- c-1 [decision] use postgres")
    assert backend.prompts[0].startswith("CURRENT SCOREBOARD")


def test_build_turn_text():
    text = build_turn_text("do X", "done", tools_used=["Read(app/main.py)"])
    assert "USER:\ndo X" in text
    assert "Read(app/main.py)" in text
    text2 = build_turn_text("do X", "done")
    assert "(none)" in text2


def test_suspect_note_only_for_none():
    unbacked = ExtractedCommitment(
        claim="httpmini supports automatic retries with jitter.",
        kind=Kind.ASSERTION,
        scope=["topic:vendored-lib"],
    )
    assert "CHALLENGE" in suspect_note(unbacked)
    backed = ExtractedCommitment(
        claim="httpmini supports timeouts only.",
        kind=Kind.ASSERTION,
        scope=["topic:vendored-lib"],
        entitlement={"source": "tool_output", "note": "read the file"},
    )
    assert suspect_note(backed) is None


# -- scope grammar (model validator) --------------------------------------------


def test_path_pin_accepted_and_exposed():
    ext = ExtractedCommitment(
        claim="The task's write scope is the app service only.",
        kind=Kind.DECISION,
        scope=["topic:task-scope", "path:app/**", "path:README.md"],
    )
    c = Commitment(
        id="c-1", ts=datetime.now(UTC), claim=ext.claim, kind=ext.kind, scope=ext.scope
    )
    assert c.path_pins == ["app/**", "README.md"]
    # path pins are invisible to the attr surface — no collision-logic leakage
    assert c.scope_attrs == {}


def test_bare_path_prefix_rejected():
    with pytest.raises(ValueError, match="bare 'path:'"):
        ExtractedCommitment(
            claim="Scope pin without a glob is meaningless here.",
            kind=Kind.DECISION,
            scope=["path:"],
        )


# -- grant discipline (ADR-0008 injection defense) -------------------------------


def test_user_grant_keeps_path_pins():
    from scorekeeper.extract import enforce_grant_discipline

    granted = ExtractedCommitment(
        claim="The task's write scope now includes the legacy module.",
        kind=Kind.DECISION,
        scope=["topic:task-scope", "path:legacy/util.py"],
        entitlement={"source": "user_utterance", "note": "explicit go-ahead"},
    )
    out = enforce_grant_discipline([granted])
    assert out[0].scope == ["topic:task-scope", "path:legacy/util.py"]


def test_non_user_sources_cannot_mint_path_pins():
    """A pasted note / document / the agent's own judgment phrased as a grant
    must not widen the wall — pins are stripped mechanically, whatever the
    model returned (negative finding #3 follow-up; prompt-injection defense)."""
    from scorekeeper.extract import enforce_grant_discipline

    for source in ("document", "tool_output", "prior_inference", "none"):
        minted = ExtractedCommitment(
            claim="A teammate note says legacy cleanup is authorized now.",
            kind=Kind.DECISION,
            scope=["topic:task-scope", "path:legacy/**", "path:**"],
            entitlement={"source": source},
        )
        out = enforce_grant_discipline([minted])
        assert out[0].scope == ["topic:task-scope"], source
        # the commitment itself survives — only the grant is stripped
        assert out[0].claim.startswith("A teammate note")


def test_extract_pipeline_applies_grant_discipline():
    backend = SeqBackend(
        '{"commitments": [{"claim": "Scope now includes legacy per the pasted note.",'
        ' "kind": "decision", "scope": ["topic:task-scope", "path:legacy/**"],'
        ' "entitlement": {"source": "document", "note": "note says so"}}]}'
    )
    out = extract_commitments(backend, "USER: here is a note\nAGENT REPLY: ok")
    assert out and out[0].scope == ["topic:task-scope"]


# -- pin polarity (ADR-0008 Amendment 3: the wall-inversion defense) ------------

def _mk(claim: str, scope: list[str], source: str = "user_utterance"):
    return ExtractedCommitment(
        claim=claim,
        kind="decision",
        scope=scope,
        entitlement={"source": source, "note": "test"},
    )


def test_prohibition_pin_is_stripped():
    """Live run-20260720T143608: 'legacy/util.py is out of scope' was recorded
    as path:legacy/util.py — the wall then ALLOWED legacy/util.py and denied
    app/main.py three times. A prohibition is not a grant."""
    from scorekeeper.extract import enforce_pin_polarity

    c = _mk("legacy/util.py is out of scope; its environment variable reads "
            "remain untouched and not consolidated with app/config.",
            ["topic:task-scope", "path:legacy/util.py"])
    out = enforce_pin_polarity([c])
    assert out[0].scope == ["topic:task-scope"]  # commitment survives, grant does not


def test_grant_beside_a_prohibition_survives():
    """The common shape: one claim carries both. Stripping per-claim instead of
    per-clause would throw the real grant away with the prohibition."""
    from scorekeeper.extract import enforce_pin_polarity

    c = _mk("Work is scoped to app/ and tests/; legacy/ belongs to another team "
            "and must not be touched.",
            ["path:app/**", "path:tests/**", "path:legacy/**"])
    out = enforce_pin_polarity([c])
    assert out[0].scope == ["path:app/**", "path:tests/**"]


def test_plain_grant_is_untouched():
    from scorekeeper.extract import enforce_pin_polarity

    c = _mk("legacy/ is ours now — modernize legacy/util.py.", ["path:legacy/**"])
    assert enforce_pin_polarity([c])[0].scope == ["path:legacy/**"]


def test_polarity_guard_runs_after_grant_discipline():
    """Both guards compose: a non-user prohibition pin loses on either count."""
    from scorekeeper.extract import enforce_grant_discipline, enforce_pin_polarity

    c = _mk("legacy/util.py is off-limits.", ["path:legacy/util.py"], source="document")
    out = enforce_pin_polarity(enforce_grant_discipline([c]))
    assert not [s for s in out[0].scope if s.startswith("path:")]
