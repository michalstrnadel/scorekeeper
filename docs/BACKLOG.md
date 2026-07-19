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
- **Scope entitlement — "the second failure mode" (Michal, 2026-07-19).
  PROMOTED to Phase 2 and SHIPPED 2026-07-19** — the "needs a dedicated
  related-work pass" precondition was satisfied by the overreach landscape sweep
  ([overreach-landscape](research/overreach-landscape.md)); the design landed as
  the entitlement-keyed scope wall (`path:` pins, ADR-0008) + DeonticBench
  `overreach`/`expansion` families with ORR/URR. Residue stays below.
- **Effort proportionality & subagent-fleet accounting (reserved axis-2
  extensions, 2026-07-19).** In-scope but *disproportionate* work (excessive
  churn for a trivial request; subagent fleets burning usage) is not scored in
  v1. Concrete design seed: the `effort_tier` field already reserved in
  DeonticBench ground truth + Diff-XYZ churn stratification (small <7 / medium
  8–24 / large >24 changed lines; >70% of SWE-bench fixes fit <100 lines) as
  the deterministic proxy, plugged into the existing TreeDiff; fleet accounting
  would key on SubagentStart-style events and Agent Contracts-style budget
  conservation — orchestrator-layer, so likely a separate surface. See
  QUESTIONS Q11.
- **AST-level scope pins (tree-sitter / ast-grep) — v2 refinement per
  ADR-0008.** Symbol-level scope (function/class nodes instead of path globs):
  whitespace-immune, semantically precise, ~66 languages — but a heavy
  per-language dependency against the stdlib-only core. Revisit if glob-level
  pins produce measurable FRR on real tasks.
- **Cross-harness ports of the scope wall.** The interception points map
  cleanly: LangGraph `__interrupt__` middleware, OpenAI Agents SDK tool
  guardrails, Cursor `preToolUse` hooks (deny without updatedInput), MCP
  gateway layer. Same board, same pins; only the deny plumbing differs.
