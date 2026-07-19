"""Commitment data model — the deontic vocabulary made into a schema (SPEC §4.2).

The Brandomian concepts map 1:1 onto fields:
- commitment       -> a Commitment record
- entitlement      -> Commitment.entitlement (provenance of the reason)
- incompatibility  -> Commitment.incompatible_with + detector verdicts
A commitment with entitlement.source == "none" is legal and significant:
it is a first-class suspect (hallucination = commitment without entitlement).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Kind(StrEnum):
    DECISION = "decision"
    ASSERTION = "assertion"
    PROMISE = "promise"
    ASSUMPTION = "assumption"


class Status(StrEnum):
    ACTIVE = "active"
    REFINED = "refined"
    SUPERSEDED = "superseded"
    CONFLICTED = "conflicted"
    RETRACTED = "retracted"


class EntitlementSource(StrEnum):
    USER_UTTERANCE = "user_utterance"
    TOOL_OUTPUT = "tool_output"
    DOCUMENT = "document"
    PRIOR_INFERENCE = "prior_inference"
    NONE = "none"


# Provenance external to the agent — the entitlement boundary (SPEC §4.3).
# A revision (operators) or a scope grant (tier0_gate) counts only when its
# source is here: the agent's own inference cannot entitle either.
EXTERNAL_SOURCES = frozenset({
    EntitlementSource.USER_UTTERANCE,
    EntitlementSource.TOOL_OUTPUT,
    EntitlementSource.DOCUMENT,
})


class Entitlement(BaseModel):
    """Provenance of the reason backing a commitment."""

    source: EntitlementSource = EntitlementSource.NONE
    refs: list[str] = Field(default_factory=list)
    note: str = ""

    @property
    def is_suspect(self) -> bool:
        """A commitment without provenance is a hallucination candidate."""
        return self.source == EntitlementSource.NONE


class Commitment(BaseModel):
    """One entry in the agent's deontic scoreboard."""

    id: str
    ts: datetime
    session: str = ""
    claim: str
    kind: Kind
    scope: list[str] = Field(default_factory=list)
    entitlement: Entitlement = Field(default_factory=Entitlement)
    consequences: list[str] = Field(default_factory=list)
    incompatible_with: list[str] = Field(default_factory=list)
    status: Status = Status.ACTIVE
    supersedes: str | None = None
    superseded_by: str | None = None

    @property
    def scope_attrs(self) -> dict[str, str]:
        """Keyed attributes in scope (``attr:key=value``) — the Tier-0 surface.

        E.g. ``attr:persistence.primary_db=postgresql`` -> {"persistence.primary_db":
        "postgresql"}. Deterministic collisions on the same key with different
        values are hard conflicts (SPEC §4.4 Tier 0).
        """
        out: dict[str, str] = {}
        for s in self.scope:
            if s.startswith("attr:") and "=" in s:
                key, _, value = s.removeprefix("attr:").partition("=")
                out[key.strip()] = value.strip()
        return out

    @property
    def topics(self) -> set[str]:
        """Topic tags in scope (``topic:...``) — candidate selection surface."""
        return {s.removeprefix("topic:") for s in self.scope if s.startswith("topic:")}

    @property
    def path_pins(self) -> list[str]:
        """Write-scope pins (``path:<glob>``) — the Tier-0 scope-wall surface
        (ADR-0008). Invisible to ``scope_attrs`` and the rival content scan by
        construction: a path grant is not a claim about content."""
        return [s.removeprefix("path:") for s in self.scope if s.startswith("path:")]


def new_id(existing: list[str], now: datetime | None = None) -> str:
    """Next id in the ``c-YYYY-MM-DD-NNNN`` series (counter is global, not per-day)."""
    now = now or datetime.now(UTC)
    max_n = 0
    for cid in existing:
        try:
            max_n = max(max_n, int(cid.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"c-{now:%Y-%m-%d}-{max_n + 1:04d}"


class ExtractedCommitment(BaseModel):
    """Write-path schema — the only door into the store (validated input to
    ``operators.apply``). Lives here, not in ``extract``: the extraction module
    is one *producer* of these; the schema itself is part of the model."""

    claim: str = Field(min_length=10, max_length=500)
    kind: Kind
    scope: list[str] = Field(default_factory=list, max_length=6)
    entitlement: Entitlement = Field(default_factory=Entitlement)
    consequences: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("scope")
    @classmethod
    def scope_prefixes(cls, v: list[str]) -> list[str]:
        for s in v:
            if not s.startswith(("topic:", "attr:", "path:")):
                raise ValueError(
                    f"scope entry must start with topic:, attr: or path: — got {s!r}"
                )
            if s.startswith("attr:") and "=" not in s:
                raise ValueError(f"attr: scope entry must be key=value — got {s!r}")
            if s.startswith("path:") and not s.removeprefix("path:").strip():
                raise ValueError("path: scope entry must carry a glob — got bare 'path:'")
        return v
