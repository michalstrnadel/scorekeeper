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

## Architecture follow-ups (audit 2026-07-19)

From the three-perspective architecture review; each verified against code, none release-blocking.

- **Unify config resolution** — one loader on `Store`, one precedence rule. Today gate/extract are env-over-config but backend selection is config-over-env (`backends/__init__.py` vs `cli.py:_gate_mode/_extract_mode`); pick env-wins everywhere and document it (needs a deprecation note for `backend.kind` pinning).
- **`extract:` config key is dead under the plugin** — `hooks.json` injects `SCOREKEEPER_EXTRACT=async`, so the config value is never consulted; also CLI default (`sync`) differs from plugin default (`async`). Drop the env injection or document the plugin override.
- **Hook-vs-MCP root divergence** — hooks resolve the store from `payload["cwd"]`, the MCP server from `SCOREKEEPER_ROOT`/cwd. The wall's deny message tells the agent to use the `supersede` MCP tool; if the two resolve different roots, the wall never lifts and nothing says why. Minimum: MCP tools report their resolved root; better: fail loudly when the resolved store doesn't exist.
- **Move `ExtractedCommitment` to `model.py`** — the "only door" input schema lives in the LLM-extraction module, forcing `operators`/`mcp_server` to import extraction machinery for a schema.
- **Backend latency budget** — retry/timeout policy varies wildly behind the `ModelBackend` protocol (openai_compat can sleep-retry minutes) while callers sit under hook deadlines; put a time budget in the protocol. Also: `ClaudeCLIBackend` should pass the system prompt via `--system-prompt` instead of folding it into the user prompt.
