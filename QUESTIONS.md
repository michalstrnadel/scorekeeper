# Open questions

Per SPEC §10.6: when the spec is unclear, record the question here and proceed with an explicitly stated assumption (logged as an `assumption` commitment in the project scoreboard).

## Naming
- **Q1. [RESOLVED 2026-07-08]** Name is `scorekeeper`, tagline "commitment tracking for LLM agents". PyPI + `michalstrnadel/scorekeeper` repo verified free. See [ADR-0001](adr/0001-project-name.md) (Accepted).

## To resolve before / during Phase 0
- **Q2. [RESOLVED 2026-07-08]** Hooks API verified against live docs. Key finding: PreCompact cannot inject into the summary → compact survival moved to SessionStart(source=compact), see [ADR-0002](adr/0002-compact-survival-via-sessionstart.md). Plugin format: `.claude-plugin/plugin.json` + `hooks/hooks.json`.
- **Q3. [RESOLVED 2026-07-08]** Cheap model string: `claude-haiku-4-5-20251001` (anthropic backend default). Backends are pluggable anyway — [ADR-0003](adr/0003-pluggable-model-backends.md).
- **Q4. [RESOLVED 2026-07-19]** `core` language: Python confirmed for v0.1 (spec §4.5). TS port deferred — now tracked as [#5](https://github.com/michalstrnadel/scorekeeper/issues/5) (Phase 3), nothing left to decide here.

## Open (Phase 0)
- **Q5.** Reference local model for the openai_compat backend — pick empirically once Ollama runs (candidates: qwen3:8b, llama3.1:8b). Golden sets are per-backend ready (`core/tests/test_extract_live.py`, `test_detect_live.py`). *2026-07-19: community data incoming via [#2](https://github.com/michalstrnadel/scorekeeper/issues/2) (first contributor volunteered); results land in `docs/model-reports/`. Decide once the first report is in.*
- **Q6.** SDK harness emulates force_compact by session restart (deterministic for both variants). Real `/compact` in a live CLI session should also be spot-checked manually before calling scenario 03 done. *2026-07-19: still pending — the one remaining manual verification step.*

## Open (Addendum-1, 2026-07-09)
- **Q7. [STANDING ASSUMPTION]** Addendum-1 references `ZMENY_ITERACE_1.md` (§3, §4, §6) — that document was never delivered to the repo. **Assumption:** the addendum is applied standalone against SPEC-cs.md and the current implementation; if ZMENY_ITERACE_1.md surfaces, reconcile. (Recorded as assumption commitment c-0016.) *Not blocking anything; closes for good if the document never surfaces.*
- **Q8. [STANDING ASSUMPTION]** Two further research documents from the same batch as the addendum's research were not imported into the repo and are not referenced by Addendum-1. **Assumption:** out of scope unless they are explicitly brought in.
- **Q9. [RESOLVED 2026-07-09]** A.3 requires "fixed seed and temperature 0" for the meta-eval — the Claude Code agent path exposes neither (SDK/CLI limitation). **Resolution (documented deviation):** the CV ≤ 0.05 gate is applied to the deterministic-configurable stages (judge at temp 0, extractor), while agent-sampling variance is handled by the A.2 statistics (Wilson CIs over repeated runs). Documented in ADR-0005 / meta-eval code — nothing left open.
- **Q10. [RESOLVED 2026-07-09]** First gate run failed (judge CV 0.056; extractor CV 0.29 via claude_cli). Resolution, refining c-0014: (a) the gate binds the **measurement instrument** — the judge, now stabilized with per-criterion median-of-3 votes; (b) the **extractor is part of the treatment under test** — its sampling variance is system behavior, reported as a diagnostic and absorbed by A.2 Wilson CIs over repeated runs, not gated as infrastructure noise (A.3's target). Judge verdict unanimity was 10/10 even in the failed run — the SCR-feeding binary was stable throughout.

## Open (the actions axis, 2026-07-19)
- **Q11.** Effort-proportionality scoring: how to score work that is *in scope but disproportionate* (entitled paths, excessive churn — e.g. a 300-line rewrite for a typo request)? Deterministic proxy identified (Diff-XYZ churn buckets: small <7 / medium 8–24 / large >24 changed lines, over the existing TreeDiff), and the `effort_tier` seam is reserved in DeonticBench ground truth — but binding a *user-chosen effort tier* to an *entitled work volume* needs a design pass (what does `effort: low` entitle, and who says so?). Deferred to the effort-proportionality backlog item; nothing scored in v1.
- **Q12. [RESOLVED 2026-07-19]** Actions-axis metric names: **ORR (Overreach Rate) / URR (Underreach Rate)**, mirroring SCR/FRR. Considered and rejected: FSR (collides with nothing but reads opaque), FRR-a (overloads the claims-axis name). Documented collisions to disambiguate at first use in print: "ORR" = Over-Refusal Rate in content-safety literature (OR-Bench lineage, Health-ORSC-Bench); ClawsBench's "SCR" = Safe Completion Rate; biometric "FRR" = False Rejection Rate. "Underreach" maps to the field's "over-abstention". See related-work.md's terminology guard.
