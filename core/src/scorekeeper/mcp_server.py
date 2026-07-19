"""scorekeeper-mcp — MCP server exposing the scoreboard to any harness (SPEC §4.5).

Intended for harness-level integration (LangGraph node, orchestrator, CI), not
for handing the agent authority over its own scoreboard: ``assert_commitment``
routes through ``operators.apply`` — the same validated door the hooks use — so
Tier-0 / Tier-1 checking and the SUPERSEDE vs BRANCH-CONFLICT gate cannot be
bypassed. ``supersede`` and ``retract`` are explicit, targeted status
transitions; they skip the pipeline by design but stay entitlement-gated
(supersede refuses non-external sources). Scaffolded, not extended —
theory.md §5.

Run: ``scorekeeper-mcp`` (stdio). Project root: $SCOREKEEPER_ROOT or cwd.
Requires the ``mcp`` extra: ``pip install "scorekeeper[mcp]"``.

Root divergence warning: hooks resolve the store from the session's cwd, this
server from $SCOREKEEPER_ROOT (or ITS cwd) — if they disagree, ``supersede``
writes a different board than the one the Tier-0 wall reads and the wall never
lifts. Every write tool therefore reports the ``root`` it acted on; set
$SCOREKEEPER_ROOT explicitly when launching the server for a project.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .backends import BackendError, detect_backend
from .detect import tier0, tier1
from .model import (
    Commitment,
    Entitlement,
    EntitlementSource,
    ExtractedCommitment,
    Kind,
    Status,
    new_id,
)
from .operators import apply as apply_operators
from .store import Store

mcp = FastMCP("scorekeeper")


def _store() -> Store:
    return Store(Path(os.environ.get("SCOREKEEPER_ROOT", ".")))


def _result_summary(result, store: Store) -> dict:
    return {
        "root": str(store.root.resolve()),  # which board was written — see module docstring
        "asserted": result.asserted,
        "supported": result.supported,
        "refined": result.refined,
        "superseded": result.superseded,
        "conflicts": [
            {"new": c.new_id, "existing": c.existing_id, "reason": c.reason}
            for c in result.conflicts
        ],
        "challenges": result.challenges,
    }


@mcp.tool()
def get_scoreboard() -> str:
    """Full human-readable scoreboard (active + superseded/retracted history)."""
    return _store().render_scoreboard()


@mcp.tool()
def get_digest() -> str:
    """Compact normative digest (< 50 lines) for context injection: conflicts
    first, then unbacked suspects, then active commitments."""
    return _store().render_digest() or "(scoreboard is empty)"


@mcp.tool()
def assert_commitment(
    claim: str,
    kind: str = "decision",
    scope: list[str] | None = None,
    source: str = "user_utterance",
    note: str = "",
    consequences: list[str] | None = None,
) -> dict:
    """Record a commitment through the full operator pipeline (Tier-0 collisions,
    Tier-1 material check when a backend is configured, SUPERSEDE vs
    BRANCH-CONFLICT by entitlement). kind: decision|assertion|promise|assumption.
    scope: 'topic:...' tags, 'attr:key=value' hard attributes, and 'path:<glob>'
    write-scope pins (entitlement-keyed Tier-0 scope wall, ADR-0008 — pins count
    only when source is external). source:
    user_utterance|tool_output|document|prior_inference|none."""
    ext = ExtractedCommitment(
        claim=claim,
        kind=Kind(kind),
        scope=scope or [],
        entitlement=Entitlement(source=EntitlementSource(source), note=note),
        consequences=consequences or [],
    )
    store = _store()
    store.init()
    try:
        backend = detect_backend(store.root)
    except BackendError:
        backend = None  # Tier-0 still runs; Tier-1 needs a model
    with store.write_lock():  # id allocation races detached workers otherwise
        return _result_summary(
            apply_operators(store, [ext], backend=backend, refs=["mcp"]), store
        )


@mcp.tool()
def check_compatibility(claim: str, scope: list[str] | None = None) -> dict:
    """Dry-run: would this claim collide with active commitments? Nothing is
    written. Returns Tier-0 attribute collisions and, when a backend is
    configured, Tier-1 material-incompatibility verdicts."""
    store = _store()
    probe = Commitment(
        id="probe", ts=datetime.now(UTC), claim=claim, kind=Kind.ASSERTION, scope=scope or []
    )
    active = store.active()
    collisions, agreements = tier0.check(probe.scope_attrs, active)
    out: dict = {
        "tier0_collisions": [
            {"key": c.key, "existing": c.existing.id, "existing_value": c.existing_value,
             "new_value": c.new_value}
            for c in collisions
        ],
        "tier0_agreements": [
            {"key": a.key, "value": a.value, "existing": a.existing.id} for a in agreements
        ],
        "tier1_verdicts": [],
    }
    try:
        backend = detect_backend(store.root)
    except BackendError:
        out["note"] = "tier0 only — no model backend configured for tier1"
        return out
    candidates = tier1.select_candidates(probe.topics, active)
    out["tier1_verdicts"] = [
        {"id": v.id, "verdict": v.verdict.value, "rationale": v.rationale}
        for v in tier1.judge(backend, claim, candidates)
    ]
    return out


@mcp.tool()
def supersede(
    old_id: str,
    claim: str,
    source: str = "user_utterance",
    note: str = "",
    scope: list[str] | None = None,
) -> dict:
    """Explicitly replace a commitment with an entitled revision (both directions
    of the chain kept; nothing deleted). source must be external to the agent:
    user_utterance|tool_output|document. scope tags the NEW claim; when omitted,
    topic:/repo: tags carry over from the old commitment but its 'attr:key=value'
    and 'path:' pins are dropped — pins encode the replaced claim's content or
    grant, and carrying them over would leave Tier-0 enforcing the OLD choice
    (or the OLD write scope) against the new one. Pass explicit 'attr:'/'path:'
    pins to keep the new choice or scope gate-protected."""
    src = EntitlementSource(source)
    if src not in (
        EntitlementSource.USER_UTTERANCE,
        EntitlementSource.TOOL_OUTPUT,
        EntitlementSource.DOCUMENT,
    ):
        raise ValueError(f"supersede requires external entitlement, got '{source}' — "
                         "an unentitled replacement is drift (use assert_commitment "
                         "and let the operators flag it)")
    store = _store()
    with store.write_lock():  # id allocation races detached workers otherwise
        old = store.load(old_id)
        if scope is None:
            scope = [s for s in old.scope if not s.startswith(("attr:", "path:"))]
        new = Commitment(
            id=new_id(store.ids()),
            ts=datetime.now(UTC),
            claim=claim,
            kind=old.kind,
            scope=scope,
            entitlement=Entitlement(source=src, note=note, refs=["mcp"]),
            supersedes=old.id,
        )
        old.status = Status.SUPERSEDED
        old.superseded_by = new.id
        store.save(old)
        store.save(new)
        store.log("SUPERSEDE", new.id, f"supersedes {old.id} (mcp)", against=old.id)
        store.write_scoreboard()
    return {"superseded": old.id, "by": new.id, "root": str(store.root.resolve())}


@mcp.tool()
def challenge(commitment_id: str, reason: str = "") -> dict:
    """Challenge a commitment's entitlement (Brandom: demand the reason). The
    commitment stays active but is logged as challenged; resolve by superseding
    it with a backed revision or retracting it."""
    store = _store()
    c = store.load(commitment_id)
    store.log("CHALLENGE", c.id, reason or "entitlement challenged via mcp")
    return {
        "challenged": c.id,
        "claim": c.claim,
        "entitlement": c.entitlement.source.value,
        "suspect": c.entitlement.is_suspect,
        "root": str(store.root.resolve()),
    }


@mcp.tool()
def retract(commitment_id: str, reason: str = "") -> dict:
    """Retract a commitment (status transition — the record is kept)."""
    store = _store()
    with store.write_lock():
        c = store.load(commitment_id)
        c.status = Status.RETRACTED
        store.save(c)
        store.log("RETRACT", c.id, reason or "retracted via mcp")
        store.write_scoreboard()
    return {"retracted": c.id, "root": str(store.root.resolve())}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
