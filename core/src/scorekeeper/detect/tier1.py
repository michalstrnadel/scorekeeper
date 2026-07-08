"""Tier 1 — material incompatibility judgment (SPEC §2.2, §4.4).

An isolated, context-poor LLM call judges whether a new commitment is
materially incompatible with scope-selected candidates. Material, not formal:
non-monotonic, content-driven, exception-aware. Precision beats recall —
a false conflict costs more than a missed one (alarm fatigue kills the tool),
so the prompt instructs: when unsure, say compatible.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError

from ..backends.base import BackendError, JSONParseError, ModelBackend, parse_json_object
from ..model import Commitment

DETECTION_SYSTEM = """\
You judge MATERIAL INCOMPATIBILITY between commitments on a coding agent's scoreboard.

Material means: judged by the content of the concepts, the way an engineer would, \
not by logical form. Material inference is non-monotonic — look for readings under \
which both commitments can stand (different environments, different components, dev \
vs prod, old vs new endpoint). Two commitments are INCOMPATIBLE only if honoring both \
at once is not coherently possible for the same artifact.

Verdicts:
- "compatible": both can bind the agent simultaneously (default when unsure — a false \
alarm is worse than a miss)
- "incompatible": no coherent reading lets both stand (e.g. primary DB is Postgres vs \
feed storage moves to MongoDB; response shape frozen vs field renamed)
- "refines": the new commitment adds specificity to the existing one without replacing \
it (Postgres -> Postgres 16.3)
- "needs_clarification": genuinely ambiguous, a human should look

Reply with ONLY a JSON object:
{"verdicts": [{"id": "<existing commitment id>", "verdict": "<see above>", \
"rationale": "<one sentence>"}]}
Include one verdict per candidate, nothing else."""


class Verdict(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    REFINES = "refines"
    NEEDS_CLARIFICATION = "needs_clarification"


class CandidateVerdict(BaseModel):
    id: str
    verdict: Verdict
    rationale: str = ""


class DetectionResult(BaseModel):
    verdicts: list[CandidateVerdict] = Field(default_factory=list)


def select_candidates(
    new_topics: set[str], active: list[Commitment], limit: int = 12
) -> list[Commitment]:
    """Scope-based candidate selection — never ship the whole scoreboard (SPEC §9)."""
    scored = [(len(new_topics & c.topics), c) for c in active]
    hits = [c for score, c in sorted(scored, key=lambda t: -t[0]) if score > 0]
    return hits[:limit]


def judge(
    backend: ModelBackend,
    new_claim: str,
    candidates: list[Commitment],
    on_error=None,
) -> list[CandidateVerdict]:
    """One isolated call over all candidates. Fails open (no verdicts) — never crashes."""
    if not candidates:
        return []
    lines = [f'- id {c.id}: [{c.kind.value}] "{c.claim}"' for c in candidates]
    user = (
        f'NEW COMMITMENT:\n"{new_claim}"\n\n'
        "EXISTING ACTIVE COMMITMENTS (candidates):\n" + "\n".join(lines)
    )
    try:
        result = DetectionResult.model_validate(
            parse_json_object(backend.complete(DETECTION_SYSTEM, user))
        )
    except (JSONParseError, ValidationError, BackendError) as e:
        if on_error:
            on_error(e)
        return []
    known = {c.id for c in candidates}
    return [v for v in result.verdicts if v.id in known]
