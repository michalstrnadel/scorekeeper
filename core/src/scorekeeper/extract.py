"""Commitment extraction from an agent turn (SPEC §4.1.2–4.1.4, ADR-0004).

Isolated, context-poor scorer call (Mercier & Sperber): the extractor sees the
turn text and the current digest — never the agent's private reasoning. Narrow
Phase-0 scope: coding decisions only. Write-path validation (Cognee lesson):
nothing enters the store unless it passes the schema; one repair retry for
weaker local models (ADR-0003), then give up silently (a missed extraction is
logged, never crashes the hook).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError, field_validator

from .backends.base import BackendError, JSONParseError, ModelBackend, parse_json_object
from .model import Entitlement, EntitlementSource, Kind

EXTRACTION_SYSTEM = """\
You are a commitment extractor for a coding agent's deontic scoreboard. You read one \
agent turn (user message + agent reply + tools the agent used) and extract the NEW \
commitments the agent undertook in that turn.

Extract ONLY high-value, binding commitments about the codebase — the kind whose later \
violation would be a real defect:
- technology/dependency choices (database, framework, library, version floors)
- API/interface contracts (response shapes, schemas, CLI flags, wire formats)
- naming and structural conventions explicitly adopted
- architectural decisions (layering, storage layout, protocols)
- promises ("I will keep X stable", "won't touch Y")
- factual assertions about the codebase or its dependencies that later work builds on

Do NOT extract: narration ("I created the file"), transient plans, style trivia, \
restatements of an existing commitment (unless it refines it).
A typical turn yields 0–3 commitments. Empty is a normal answer.

For each commitment judge the ENTITLEMENT — the provenance of the reason behind it:
- "user_utterance": the user decided/stated/constrained it in this turn or visibly earlier
- "tool_output": the agent learned it by reading files or running code THIS turn
- "document": it comes from docs/specs in the repo the agent actually opened
- "prior_inference": derived from already-scoreboarded commitments
- "none": the agent asserted it with NO visible basis (answered from priors without \
reading anything). Be strict: if the turn shows no tool use backing a factual claim \
about code/libraries, the source is "none".

Reply with ONLY a JSON object, no prose:
{"commitments": [{
  "claim": "<one self-contained sentence>",
  "kind": "decision" | "assertion" | "promise" | "assumption",
  "scope": ["topic:<area>", "attr:<key>=<value>", ...],
  "entitlement": {"source": "<see above>", "note": "<why, one clause>"},
  "consequences": ["<optional inferential consequence>", ...]
}]}

Scope rules: 1–3 "topic:" tags (lowercase, dashed). Add an "attr:key=value" entry ONLY \
for hard, checkable attributes (attr:persistence.primary_db=postgresql, \
attr:python.min_version=3.10, attr:api.users.response_shape=flat_id_name_email); \
normalize value to lowercase snake/dotted form.
"""


class ExtractedCommitment(BaseModel):
    """Write-path schema — the only door into the store."""

    claim: str = Field(min_length=10, max_length=500)
    kind: Kind
    scope: list[str] = Field(default_factory=list, max_length=6)
    entitlement: Entitlement = Field(default_factory=Entitlement)
    consequences: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("scope")
    @classmethod
    def scope_prefixes(cls, v: list[str]) -> list[str]:
        for s in v:
            if not (s.startswith("topic:") or s.startswith("attr:")):
                raise ValueError(f"scope entry must start with topic: or attr: — got {s!r}")
            if s.startswith("attr:") and "=" not in s:
                raise ValueError(f"attr: scope entry must be key=value — got {s!r}")
        return v


class ExtractionResult(BaseModel):
    commitments: list[ExtractedCommitment] = Field(default_factory=list, max_length=8)


def build_turn_text(user: str, assistant: str, tools_used: list[str] | None = None) -> str:
    parts = [f"USER:\n{user}", f"AGENT REPLY:\n{assistant}"]
    parts.append(
        "TOOLS THE AGENT USED THIS TURN:\n"
        + ("\n".join(f"- {t}" for t in tools_used) if tools_used else "(none)")
    )
    return "\n\n".join(parts)


def extract_commitments(
    backend: ModelBackend,
    turn_text: str,
    digest: str = "",
    on_error=None,
) -> list[ExtractedCommitment]:
    """One extraction call + one repair retry. Returns [] on unrecoverable failure."""
    user = turn_text
    if digest:
        user = f"CURRENT SCOREBOARD (for context — do not re-extract these):\n{digest}\n\n{user}"

    def attempt(prompt: str) -> ExtractionResult:
        raw = backend.complete(EXTRACTION_SYSTEM, prompt)
        return ExtractionResult.model_validate(parse_json_object(raw))

    try:
        return attempt(user).commitments
    except (JSONParseError, ValidationError) as first_err:
        repair = (
            f"{user}\n\nYour previous reply was invalid: {first_err}\n"
            "Reply again with ONLY the JSON object in the required schema."
        )
        try:
            return attempt(repair).commitments
        except (JSONParseError, ValidationError, BackendError) as second_err:
            if on_error:
                on_error(second_err)
            return []
    except BackendError as e:
        if on_error:
            on_error(e)
        return []


def suspect_note(c: ExtractedCommitment) -> str | None:
    """Human-readable CHALLENGE line for an unbacked commitment, else None."""
    if c.entitlement.source != EntitlementSource.NONE:
        return None
    return (
        f"CHALLENGE: '{c.claim}' was asserted without provenance "
        "(no user statement, no file read, no tool output). Verify it or retract it."
    )
