"""The seven operators (SPEC §4.3) — the project's core distinction lives here.

SUPERSEDE vs BRANCH-CONFLICT is exactly the boundary between an *entitled*
revision of a commitment and unbacked drift (BeliefShift's BRA/ESI, made
explicit). Phase-0 policy: a revision is entitled when its provenance is
external to the agent — user_utterance, tool_output, or document. Revisions
grounded only in prior_inference or nothing are drift.

Nothing is ever deleted; statuses transition and both directions of the
supersedes chain are kept (DCPM pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .backends.base import ModelBackend
from .detect import tier0, tier1
from .detect.tier1 import Verdict
from .extract import ExtractedCommitment
from .model import Commitment, EntitlementSource, Status, new_id
from .store import Store

ENTITLED_TO_REVISE = {
    EntitlementSource.USER_UTTERANCE,
    EntitlementSource.TOOL_OUTPUT,
    EntitlementSource.DOCUMENT,
}


@dataclass
class Conflict:
    new_id: str
    existing_id: str
    reason: str


@dataclass
class ApplyResult:
    asserted: list[str] = field(default_factory=list)
    supported: list[str] = field(default_factory=list)
    refined: list[tuple[str, str]] = field(default_factory=list)      # (old, new)
    superseded: list[tuple[str, str]] = field(default_factory=list)   # (old, new)
    conflicts: list[Conflict] = field(default_factory=list)
    challenges: list[str] = field(default_factory=list)               # unbacked commitment ids

    @property
    def has_findings(self) -> bool:
        return bool(self.conflicts or self.challenges)


def _materialize(
    store: Store, ext: ExtractedCommitment, session: str, refs: list[str]
) -> Commitment:
    c = Commitment(
        id=new_id(store.ids()),
        ts=datetime.now(UTC),
        session=session,
        claim=ext.claim,
        kind=ext.kind,
        scope=ext.scope,
        entitlement=ext.entitlement.model_copy(update={"refs": refs}),
        consequences=ext.consequences,
    )
    return c


def _supersede(store: Store, old: Commitment, new: Commitment, result: ApplyResult) -> None:
    old.status = Status.SUPERSEDED
    old.superseded_by = new.id
    new.supersedes = old.id
    store.save(old)
    store.log("SUPERSEDE", new.id, f"supersedes {old.id}", against=old.id)
    result.superseded.append((old.id, new.id))


def _refine(store: Store, old: Commitment, new: Commitment, result: ApplyResult) -> None:
    old.status = Status.REFINED
    old.superseded_by = new.id
    new.supersedes = old.id
    store.save(old)
    store.log("REFINE", new.id, f"refines {old.id}", against=old.id)
    result.refined.append((old.id, new.id))


def _branch_conflict(
    store: Store, old: Commitment, new: Commitment, reason: str, result: ApplyResult
) -> None:
    old.status = Status.CONFLICTED
    new.status = Status.CONFLICTED
    if new.id not in old.incompatible_with:
        old.incompatible_with.append(new.id)
    if old.id not in new.incompatible_with:
        new.incompatible_with.append(old.id)
    store.save(old)
    store.log("BRANCH-CONFLICT", new.id, reason, against=old.id)
    result.conflicts.append(Conflict(new.id, old.id, reason))


def apply(
    store: Store,
    extracted: list[ExtractedCommitment],
    backend: ModelBackend | None = None,
    session: str = "",
    refs: list[str] | None = None,
) -> ApplyResult:
    """Run each extracted commitment through Tier 0 (+ Tier 1 when a backend is given)
    and write the outcome. The scoreboard file is regenerated at the end."""
    result = ApplyResult()
    refs = refs or []

    for ext in extracted:
        active = store.active()

        # exact duplicate claim -> SUPPORT (extend refs, no new record)
        dup = next(
            (c for c in active if c.claim.strip().lower() == ext.claim.strip().lower()), None
        )
        if dup is not None:
            dup.entitlement.refs.extend(r for r in refs if r not in dup.entitlement.refs)
            store.save(dup)
            store.log("SUPPORT", dup.id, "duplicate claim re-asserted")
            result.supported.append(dup.id)
            continue

        new = _materialize(store, ext, session, refs)
        entitled = new.entitlement.source in ENTITLED_TO_REVISE

        # --- Tier 0: hard attribute collisions --------------------------------
        collisions, agreements = tier0.check(new.scope_attrs, active)
        handled = set()
        for ag in agreements:
            if ag.existing.id in handled:
                continue
            store.log("SUPPORT", ag.existing.id, f"agreement on {ag.key}={ag.value} by {new.id}")
            result.supported.append(ag.existing.id)
        for col in collisions:
            if col.existing.id in handled:
                continue
            handled.add(col.existing.id)
            reason = (
                f"tier0: {col.key} — existing '{col.existing_value}' vs new '{col.new_value}'"
            )
            if not entitled:
                _branch_conflict(store, col.existing, new, reason, result)
                continue
            # Entitled revision: a same-key collision is not yet a replacement — the
            # pair may coexist under a non-monotonic reading (dev cache vs prod cache,
            # Phase-0 finding F2). Confirm materially with Tier 1 before superseding;
            # without a backend, keep the deterministic supersede.
            verdicts = tier1.judge(backend, new.claim, [col.existing]) if backend else []
            v = verdicts[0] if verdicts else None
            if v is not None and v.verdict == Verdict.REFINES:
                _refine(store, col.existing, new, result)
            elif v is not None and v.verdict in (Verdict.COMPATIBLE, Verdict.NEEDS_CLARIFICATION):
                store.log(
                    "COEXIST", new.id, f"{reason} — waived by tier1: {v.rationale}",
                    against=col.existing.id,
                )
            else:
                _supersede(store, col.existing, new, result)

        # --- Tier 1: material incompatibility over scope candidates -----------
        if backend is not None:
            candidates = [
                c for c in tier1.select_candidates(new.topics, active) if c.id not in handled
            ]
            for v in tier1.judge(backend, new.claim, candidates):
                if v.id in handled:
                    continue
                existing = next(c for c in candidates if c.id == v.id)
                if v.verdict == Verdict.INCOMPATIBLE:
                    handled.add(v.id)
                    if entitled:
                        _supersede(store, existing, new, result)
                    else:
                        _branch_conflict(store, existing, new, f"tier1: {v.rationale}", result)
                elif v.verdict == Verdict.REFINES and entitled:
                    handled.add(v.id)
                    _refine(store, existing, new, result)

        # --- write + CHALLENGE unbacked ---------------------------------------
        store.save(new)
        if not result.superseded or result.superseded[-1][1] != new.id:
            store.log("ASSERT", new.id, new.claim)
        result.asserted.append(new.id)
        if new.entitlement.source == EntitlementSource.NONE:
            store.log("CHALLENGE", new.id, "commitment without entitlement")
            result.challenges.append(new.id)

    store.write_scoreboard()
    return result
