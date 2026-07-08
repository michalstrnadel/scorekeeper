# Open questions

Per SPEC §10.6: when the spec is unclear, record the question here and proceed with an explicitly stated assumption (logged as an `assumption` commitment in the project scoreboard).

## Naming
- **Q1. [RESOLVED 2026-07-08]** Name is `scorekeeper`, tagline "commitment tracking for LLM agents". PyPI + `michalstrnadel/scorekeeper` repo verified free. See [ADR-0001](adr/0001-project-name.md) (Accepted).

## To resolve before / during Phase 0
- **Q2. [RESOLVED 2026-07-08]** Hooks API verified against live docs. Key finding: PreCompact cannot inject into the summary → compact survival moved to SessionStart(source=compact), see [ADR-0002](adr/0002-compact-survival-via-sessionstart.md). Plugin format: `.claude-plugin/plugin.json` + `hooks/hooks.json`.
- **Q3. [RESOLVED 2026-07-08]** Cheap model string: `claude-haiku-4-5-20251001` (anthropic backend default). Backends are pluggable anyway — [ADR-0003](adr/0003-pluggable-model-backends.md).
- **Q4.** `core` language: Python confirmed for v0.1 (spec §4.5). TS port deferred.

## Open (Phase 0)
- **Q5.** Reference local model for the openai_compat backend — pick empirically once Ollama runs (candidates: qwen3:8b, llama3.1:8b). Golden sets are per-backend ready (`core/tests/test_extract_live.py`, `test_detect_live.py`).
- **Q6.** SDK harness emulates force_compact by session restart (deterministic for both variants). Real `/compact` in a live CLI session should also be spot-checked manually before calling scenario 03 done.
