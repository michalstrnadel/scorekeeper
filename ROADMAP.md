# Roadmap

English summary of the plan. The canonical, detailed specification is [`docs/SPEC-cs.md`](docs/SPEC-cs.md) §7 (Czech — kept as the source-of-record vision; English translation: [`docs/SPEC.md`](docs/SPEC.md)).

Status legend: ✅ done · 🚧 in progress · ⬜ planned

## Phase 0 — Mechanism & signal ✅

Prove the overlay works end-to-end and catches drift a bare agent lets through.

- ✅ Core: commitment model, transparent store, the seven operators (the SUPERSEDE-vs-BRANCH-CONFLICT distinction)
- ✅ Claude Code plugin (hooks) + Agent-SDK eval harness + planted scenarios
- ✅ Local, cross-family judge (qwen3 via Ollama) — no cloud dependency
- ✅ **Acceptance gate passed** — on a planted db-choice task the bare agent drifted to MongoDB; the scorekept twin held. FPR 0, +0.6% overhead, commitment survived compaction. [Full report](bench/results/PHASE0-REPORT.md).

## Phase 1 — Library & robustness (v0.1) ✅

Make it installable and usable by anyone.

- ✅ `pip install scorekeeper` ([PyPI](https://pypi.org/project/scorekeeper/)) — core + CLI
- ✅ **One-command Claude Code install** via plugin marketplace; the scorer self-resolves (pip/uvx), no API key needed
- ✅ MCP server (`scorekeeper-mcp`) — writes route through the same operator pipeline as the hooks
- ✅ Async extraction (detached worker, ~0 ms added turn latency; [ADR-0006](adr/0006-async-extraction.md))
- ✅ Environment-scoped attributes (Phase-0 finding F2 fix)

## Phase 2 — DeonticBench & evidence 🚧

Turn the qualitative result into a rate with confidence intervals.

- ✅ Procedural benchmark generator (drift & revision families; distance / compaction / distractor knobs; dev/eval split)
- ✅ Ablation harness (leave-one-out: `no-digest`, `no-tier0`, `no-stopblock`, `silent` placebo; gate modes `blocking`/`bump`) + deterministic behavioral classifier
- ✅ First verified paired run on the hardest condition reproduces the effect ([progress report](bench/results/DEONTICBENCH-PROGRESS.md))
- 🚧 **Scale it** — many seeds × conditions × families for effect sizes. *We'd rather the community run this than scale it in-house* — see [How to help](#how-to-help).
- ✅ Revision-family classifier ([#4](https://github.com/michalstrnadel/scorekeeper/issues/4)) — `classify_revision` + FRR (false-refusal rate) in run summaries
- ✅ **The second axis — "No barging" (ADR-0008, 2026-07-19):** entitlement-keyed Tier-0 scope wall (`path:` pins; out-of-scope writes denied until the board records an entitled widening) + DeonticBench `overreach`/`expansion` families with the ORR/URR metric pair (isogenic sibling pairs, seed-vs-final tree-diff classifier). *Mechanism shipped and unit-tested; first live paired runs (2026-07-19/20) are a case series, not rates — the drive-by was elicited only under forced compaction, where the overlay closed it, and the runs surfaced three defects in the prose→pin translation, now fixed (ADR-0008 Amendments 1–3). No rates until the powered set lands ([evidence report](bench/results/SMOKE-SCOPE-REPORT.md)).*
- 🚧 Live paired runs for the actions axis (bare vs `blocking-claims-only` vs `blocking`; run design per [overreach-landscape §6](docs/research/overreach-landscape.md))
- ⬜ Public dataset + leaderboard

## Phase 3 — Broader integrations & write-up ⬜

- ⬜ TypeScript port of the core ([#5](https://github.com/michalstrnadel/scorekeeper/issues/5))
- ⬜ LangGraph node; Letta plugin
- ⬜ Multi-agent shared scoreboard (social scorekeeping, literally)
- ⬜ "Normative dream" mode — async off-hours audit of the board
- ✅ **Rename the benchmark** — done 2026-07-19: now **DeonticBench** (the working name "EntitleBench" collided with an established SE/NLP benchmark — commit-message generation, 1.6M commits; [related-work](docs/research/related-work.md))
- ⬜ Paper / technical report (the philosophical grounding: Brandom's scorekeeping, Sterelny's scaffolded mind). Decision 2026-07-19: **no NeurIPS-workshop submission** — the write-up proceeds as an arXiv technical report on its own clock, evidence-first (live paired runs land before drafting); conference venues (AAMAS 2027, ICLR 2027 per the [related-work map](docs/research/related-work.md)) reconsidered once the numbers exist. The [submission checklist](docs/paper/submission-checklist.md) still gates any eventual upload.

## How to help

The project is early and the design is the artifact right now — **trying it and reporting back is as valuable as code.**

- Run it and file an [experience report](https://github.com/michalstrnadel/scorekeeper/issues/new?template=experience-report.md) (what it caught, missed, or got wrong)
- Pick a [good first issue](https://github.com/michalstrnadel/scorekeeper/issues?q=is%3Aopen+label%3A%22good+first+issue%22) — extend the rival-tech lexicon, add a scenario, try a new local model
- See [CONTRIBUTING.md](CONTRIBUTING.md)
