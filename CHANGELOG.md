# Changelog

## 0.1.1 — 2026-07-10

Re-release with the sdist included. PyPI permanently retires filenames of deleted projects; a previous (unrelated, since-deleted) `scorekeeper` project had burned `scorekeeper-0.1.0.tar.gz`, so 0.1.0 shipped wheel-only. No code changes.

## 0.1.0 — 2026-07-10

First packaged release (`pip install scorekeeper`). Phase 0 acceptance gate passed — see `bench/results/PHASE0-REPORT.md`.

### Added
- **MCP server** (`scorekeeper-mcp`, extra `[mcp]`): `get_scoreboard`, `get_digest`, `assert_commitment`, `check_compatibility` (dry-run), `supersede`, `challenge`, `retract`. All writes route through the operator pipeline — the agent cannot bypass the scorer.
- **Async extraction** (ADR-0006): Stop hook spawns a detached worker (~0 ms added turn latency); findings surface on the next user prompt via the new `UserPromptSubmit` hook. Plugin defaults to async; library defaults to sync. `SCOREKEEPER_EXTRACT=async|sync`.
- Demo GIF + `demo/drift_demo.py` (30-second mechanism walkthrough, no LLM needed).
- Release workflow (PyPI trusted publishing on `v*` tags).

### Fixed
- **F2 (Phase-0 finding):** an entitled revision colliding on a Tier-0 attribute key no longer supersedes blindly — Tier-1 confirms material replacement first (coexisting environments stay separate commitments; `refines` refines). Extraction prompt now scopes attributes by environment (`attr:caching.backend.dev=…`). Unentitled drift remains a deterministic, zero-LLM catch.

## 0.0.1 — 2026-07-08 … 2026-07-10 (unreleased)

Phase 0: core model/store/operators, pluggable backends (local OSS first-class), Claude Code plugin (4 hooks), planted-scenario benchmark + Agent-SDK harness, local cross-family judge (qwen3, S8 protocol), 12-run acceptance matrix.
