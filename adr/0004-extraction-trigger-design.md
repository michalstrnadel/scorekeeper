# ADR-0004: Extraction trigger — Stop hook once per turn; PostToolUse(Edit|Write) runs Tier-0 only

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

Commitment extraction is an LLM call; running it after every tool use would multiply cost and latency 10–50× per turn and risk alarm fatigue (SPEC §9). Running it too rarely risks the reliability gap. Deterministic triggers are a project principle (SPEC §4.1.2) — the question is *which* deterministic triggers.

## Decision

- **`Stop` hook** — the single extraction point: once per agent turn, reads the completed turn from `transcript_path`, extracts commitments (1 LLM call), applies operators, runs Tier-1 on scope-selected candidates.
- **`PostToolUse` with matcher `Edit|Write`** — no LLM: only the deterministic Tier-0 scope-key check against files/keys touched, so hard collisions (tech choices, versions, contracts) are flagged *immediately*, mid-turn, at ~ms cost.
- **`SessionStart`** — digest injection (ADR-0002). **`PreCompact`** — audit backup.

Overhead budget: ~1 cheap-model call per turn, well under the SPEC's <10 % token target.

## Consequences

- A commitment asserted and contradicted *within the same turn* is caught at turn end (Stop), not instantly — acceptable for Phase 0; revisit if scenarios show it matters.
- Batch extraction of a whole turn gives the extractor more context than per-tool snippets — expected to help precision.
