# Backlog

## P1 (Phase 1)

- **Async extraction mode for the Stop hook** (runtime latency is sacred — Michal, 2026-07-09): fire extraction in the background so turn-end latency stays ~0; conflicts/challenges are delivered one turn later via the existing digest injection (UserPromptSubmit/SessionStart). Tier-0 stays synchronous (~ms) so hard collisions are still caught instantly. DCPM System-1/System-2 pattern at single-turn scale. Measure both modes in the P90/P99 report; sync remains available for max-strictness setups.

## P2 (Phase 1–2)

Per Addendum-1 §C; items land in Phase 1–2 unless pulled earlier.

- **xAIF export** — `scorekeeper export --format xaif` (mapping: [interop.md](interop.md) §1); unlocks OVA visualization + oAMF pipelines.
- **PROV-JSON export** — `scorekeeper export --format prov-json` ([interop.md](interop.md) §2).
- **OpenTelemetry emitter** — span events `commitment.asserted`, `conflict.detected`, `challenge.raised` for Langfuse/LangSmith/AgentOps users.
- **`scorekeeper report` UI** (Addendum-1 §B.3): split-pane chronology + time-travel commitment graph over the append-only log; superseded nodes dimmed not removed; conflict = red CA-edge between two live nodes; scope-cluster collapsing; optional Sankey provenance view (PROV-O-Viz pattern).
- **Game Engine Separation** for DeonticBench publication: public engine/rules/generator, private held-out eval instances (TCG-Bench pattern).
- **Search-time contamination sandbox** for Phase-2 eval runs (denylist: HuggingFace, GitHub, forums).
- **Concept-drift audit**: rerun the fixed golden sets on every minor release and before any published number.
- **CyclicJudge**: round-robin second judge family (Addendum-1 §A.1).
- **AgentDiet hypothesis** (Addendum-1 §A.6): H — post-compaction digest condition uses ≤ tokens of the bare condition at higher consistency; test in Phase 2 ablations.


## Architecture follow-ups (audit 2026-07-19) — RESOLVED 2026-07-19

All five landed the same day: env-over-config precedence unified in `detect_backend`
(explicit `SCOREKEEPER_MODEL_URL` wins; config fills gaps; passive auto-detect last);
the plugin's `hooks.json` now sets `SCOREKEEPER_EXTRACT_DEFAULT` so the config
`extract:` key works under the plugin again (precedence: user env > config > surface
default > sync); MCP write tools report the `root` they acted on and the server
docstring documents the hook-vs-MCP divergence trap; `ExtractedCommitment` moved to
`model.py` (re-exported from `extract` and top-level); `OpenAICompatBackend` gained a
total retry `budget` (180s default, matching the Stop-hook deadline) and
`ClaudeCLIBackend` passes the system prompt via `--append-system-prompt`.

## P3 (Phase 3 candidates)

- **Normative dream mode — now with a proven loop shape** (updated 2026-07-19 per
  [self-improvement-landscape](research/self-improvement-landscape.md)): adopt the
  Self-Harness pattern (arXiv:2606.09498) — *weakness mining → bounded proposal →
  validation with regression gating*. Weakness mining = the audit log (gate denies,
  false conflicts, per-backend repair-retry counts from `model-reports/`); bounded
  proposals = lexicon families, extraction prompts, tier thresholds — never operator
  semantics, never the board; regression gate = golden sets + DeonticBench dev split;
  protected grader = the scoreboard and operator pipeline, which the loop must never
  edit. Every accepted change logged with the weakness it addressed and its regression
  test. Not before Phase-2 evidence ships.
- **Scope entitlement — "the second failure mode" (Michal, 2026-07-19; exploratory).**
  V1 of the thesis catches *claiming without entitlement* (hallucination/drift —
  "you're bluffing"); the symmetric failure is *acting without entitlement* —
  over-eager agents doing large amounts of unrequested work (subagent fleets, drive-by
  refactors, burned usage — "slow down"). Same Brandomian structure applied to deeds:
  the user's request + chosen effort level entitles a bounded scope of action; work
  outside it is unentitled. Deterministically checkable proxies exist: files touched
  outside a scope pin (`attr:task.scope=...`), subagent spawns / tool-call counts vs.
  an effort commitment. Candidate DeonticBench family: "overreach" — planted temptation
  to over-scope, ground truth = the set of files that must NOT change; symmetric
  metrics carry over (over-blocking eagerness = the FRR analog). Needs a dedicated
  related-work pass before any design commitment (does anyone benchmark agent
  over-scoping?).
