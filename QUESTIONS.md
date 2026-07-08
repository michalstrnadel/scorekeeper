# Open questions

Per SPEC §10.6: when the spec is unclear, record the question here and proceed with an explicitly stated assumption (logged as an `assumption` commitment in the project scoreboard).

## Naming
- **Q1. [RESOLVED 2026-07-08]** Name is `scorekeeper`, tagline "commitment tracking for LLM agents". PyPI + `michalstrnadel/scorekeeper` repo verified free. See [ADR-0001](adr/0001-project-name.md) (Accepted).

## To resolve before / during Phase 0
- **Q2.** Exact current Claude Code hooks API + plugin mechanism — verify against live docs (code.claude.com/docs) at implementation time, not against the spec.
- **Q3.** Current cheap-model string for the extractor/detector (Haiku-class) — verify at implementation time.
- **Q4.** `core` language: Python confirmed for v0.1 (spec §4.5). TS port deferred.
