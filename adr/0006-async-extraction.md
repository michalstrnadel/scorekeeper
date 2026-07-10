# ADR-0006: Async extraction — detached worker; findings drain on the next user prompt

- **Status:** Accepted
- **Date:** 2026-07-10

## Context

The sync Stop hook holds the turn open for the whole extraction pipeline (extract → operators → Tier-1), i.e. seconds of LLM latency appended to *every* agent turn. Runtime latency is a hard product constraint (Phase-0 decision: "nesmíme zpomalit nic"), and Phase-0 finding F1 showed the dominant steering channel is the *digest*, not the in-turn block — so the block's timing is less load-bearing than the SPEC assumed.

## Decision

- **`Stop` hook (async mode):** writes the hook payload to `.scorekeeper/worker/` and spawns a detached worker process (`python -m scorekeeper worker <payload>`); the hook returns immediately — extraction adds ~0 ms to the turn.
- **Worker:** runs the identical pipeline (`_extract_findings`, shared with sync mode), serialized per store via `flock` (concurrent sessions must not interleave id allocation), appends findings to `.scorekeeper/pending-findings.md`, never raises.
- **`UserPromptSubmit` hook (new):** drains `pending-findings.md` into `additionalContext` — conflicts and challenges surface at the start of the next turn, still in-conversation, before the agent builds further.
- **Mode selection:** `SCOREKEEPER_EXTRACT=async|sync` env, then `config.yaml` `extract:`, default **sync** in the library (deterministic, benchmarkable — the Phase-0 measured configuration). The Claude Code plugin sets **async** as its default (user-overridable via env).

## Consequences

- Findings arrive one turn later than in sync mode. Mitigated by: Tier-0 content scan still fires mid-turn (ms, sync), and the digest still steers every session start. CommitBench should measure the sync-vs-async catch-latency delta explicitly.
- A turn-final conflict in the *last* turn of a session surfaces only via the next `SessionStart` digest (conflicts sort first there by design).
- Two processes may extract for the same store; `flock` serializes writes. Payload files are consumed (deleted) by the worker; `worker.log` holds stderr for debugging.
