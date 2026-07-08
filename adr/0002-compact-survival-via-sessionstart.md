# ADR-0002: Compaction survival via SessionStart(source=compact), not PreCompact injection

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

SPEC §4.5 assumed the `PreCompact` hook could inject the normative scoreboard digest *into* the compaction summary. Verification against live Claude Code documentation (July 2026) shows this is wrong: **PreCompact can only read the transcript and block/allow compaction** — there is no field for injecting content into or modifying the summarization.

However, `SessionStart` fires with `source: "compact"` immediately after compaction completes, and its output supports `additionalContext` — content injected into the fresh post-compaction context.

## Decision

The "key moment" mechanism moves one step later in the lifecycle:

- **`SessionStart` (all sources: `startup`, `resume`, `clear`, `compact`)** injects the scoreboard digest (< 50 lines) via `additionalContext`. The `compact` source is the survival path: the digest re-enters context right after the summarizer has dropped it.
- **`PreCompact`** is retained for a different job: audit backup of the full scoreboard state before compaction (no blocking, no injection).

Net effect is equivalent to the SPEC's intent — normative structure survives compaction while narrative is dropped — with a cleaner separation: the summarizer is left alone; the scoreboard re-asserts itself after.

## Consequences

- Plugin `hooks.json` registers SessionStart with no source filter; the digest generator must be fast (no LLM call — pure store read).
- The eval harness scenario 3 (decision → forced compact → temptation) tests exactly this path.
- SPEC §4.5 wording is superseded by this ADR; scoreboard commitment updated via SUPERSEDE (entitlement: verified live documentation — `tool_output`).
