# Changelog

## 0.2.0 — 2026-07-14

First release with the blocking Tier-0 gate. Also the first release after a
37-agent adversarial audit of the plugin→scorer chain (triggered by #6);
everything it confirmed is fixed below.

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
- **Marketplace install no longer blocks all Edit/Write on a version-skewed scorer** (#6). The plugin's `PreToolUse` hook invokes `hook pre-tool-use`, which the published 0.1.1 CLI doesn't know; its argparse error (exit 2) propagated through `run.sh`'s `exec` and Claude Code read it as a deny. `run.sh` now treats any non-zero scorer exit as infrastructure and exits 0 — safe because a legitimate gate deny is always JSON-on-stdout with exit 0, never a non-zero exit.
- **Audit fixes — gate precision** (all regression-tested):
  - `NotebookEdit` no longer bypasses the gate and the advisory channel (matcher + the `new_source` field are now scanned).
  - Shell writes are **audited**: a `Bash` PostToolUse hook logs `TIER0-SHELL-AUDIT` on rival tokens in commands (log-only — no warning; `grep` is not drift). The wall's "every workaround is audited" sentence is now true.
  - An Edit's `old_string` is a **suppressor, never a trigger**: the edit that *removes* the rival (fixing drift) was warned by the advisory channel and — worse — permanently denied by the wall. Rivals already present in the replaced text no longer count as new conflicts.
  - Documentation files (`.md`/`.rst`/`.txt`) are exempt from the blocking gate: prose arguing *about* the rival ("Memcached was evaluated and rejected") was an unescapable deny. The advisory warning still fires there.
  - Bump mode fails **open** when its deny state cannot persist (disk full etc.) — it had promised "the retry will not be blocked" and then re-denied forever.
- **Audit fixes — concurrency** (all regression-tested):
  - One `Store.write_lock()` now serializes every writer: the async worker, the sync Stop hook, and the MCP write tools raced on id allocation and could silently overwrite each other's records.
  - Commitment records and the scoreboard are written **atomically** (tmp + `os.replace`): a gate racing a worker could read a truncated YAML and silently skip its check (~10 % empty reads in the race repro).
  - The pending-findings drain runs under the worker lock (non-blocking: skips a turn instead of stalling): findings appended between the unlocked read and unlink were deleted unread.
- **Audit fixes — dispatcher (`run.sh`)**:
  - A failed resolver now **falls through** to the next one instead of ending the chain — a stale `pip install scorekeeper` permanently masked a working uvx one line below.
  - The uvx/pipx paths pin a **minimum scorer version** (`scorekeeper>=0.2.0`) released in lockstep with the plugin, so hooks.json can never again advertise an event no published scorer knows; release.yml enforces the lockstep across pyproject, `__version__`, plugin.json, marketplace.json, and the pin.
  - PATH candidates are **appended**, not prepended — run.sh no longer shadows the user's own PATH preference with a stale `pip --user` install.
  - A completely dead scorer announces itself once per session (SessionStart context line) instead of failing silently forever.
- **Packaging**: wheel/sdist now ship the LICENSE file and the `py.typed` marker; `scorekeeper.__version__` (stuck at 0.0.1) is bumped and lockstep-checked at release.
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
