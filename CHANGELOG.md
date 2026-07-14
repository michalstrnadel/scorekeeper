# Changelog

## Unreleased

### Changed
- **The benchmark is now EntitleBench** (formerly the working name CommitBench — collision with the established commit-message-generation benchmark). Module `bench/entitlebench/`, progress doc `ENTITLEBENCH-PROGRESS.md`; dated evidence artifacts keep the historical name.
- **Gate v2 verified symmetrically** on the seed-0 scenario every softer channel failed: drift family **HELD/high** (2 denies, no rival code landed, agent surfaced) and revision family **EXECUTED/high with zero denies** (turn-end extraction recorded the entitled SUPERSEDE before any conflicting write). See `bench/results/SMOKE-DRIFT-S0-REPORT.md`.

### Added
- **`docs/why.md`** — the argument in accessible form (scoreboard vs. memory), linked from the README; `docs/theory.md` gains **§6b on Truth Maintenance Systems** (Doyle 1979, de Kleer 1986) as the second acknowledged lineage, with the TMS-vs-scorekeeper differentiation spelled out.
- **One-command install** via a Claude Code plugin marketplace (`.claude-plugin/marketplace.json`): `/plugin marketplace add michalstrnadel/scorekeeper` then `/plugin install scorekeeper@scorekeeper`.
- The plugin dispatcher (`hooks/run.sh`) now **self-resolves the scorer**: installed CLI → in-repo `core/` (uv) → `uvx`/`pipx` fetch from PyPI on first run. A marketplace install needs no manual `pip install`. It also prepends the usual install dirs to PATH (hooks run in a non-interactive shell).
- Contributor onboarding: `CONTRIBUTING.md`, issue templates (incl. `experience-report`), PR template, `CODE_OF_CONDUCT.md`, `CITATION.cff`; README "Try it in 60 seconds".
- EntitleBench (Phase 2) tooling: procedural generator + ablation harness + deterministic behavioral classifier. See `bench/results/ENTITLEBENCH-PROGRESS.md`.
- Revision-family classifier (`classify_revision`, #4): scores whether the agent executed a user-ordered, entitled migration (EXECUTED) or falsely obstructed it (REFUSED). Run summaries now report FRR (false-refusal rate) alongside SCR.
- **Blocking Tier-0 gate** (ADR-0007, opt-in): `tier0_gate: block` in `.scorekeeper/config.yaml` (or `SCOREKEEPER_TIER0_GATE=block`) denies a Write/Edit conflicting with a pinned commitment **until the scoreboard itself records an entitled revision** (supersede via the MCP tool or extraction of the user's order) — the agent's self-attested entitlement cannot lift it. A one-shot `bump` mode is kept for ablations after being measurably exploited (the agent claimed a pasted draft note as its entitlement, retried, and drifted anyway — `bench/results/SMOKE-DRIFT-S0-REPORT.md`). Denies audited as `TIER0-GATE-DENY`; bench variants `blocking` (wall) and `bump` A/B-test the channels. Born from a verified negative finding: advisory warnings alone did not stop a weaker model from drifting.

### Fixed
- Rebuilt the demo GIF so the drift-vs-SUPERSEDE contrast is legible in one frame.

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
