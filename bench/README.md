# DeonticBench

Benchmark for an agent's consistency with its **own** commitments — the gap no existing benchmark fills (BeliefShift measures consistency with the *user's* beliefs; Logic Haystacks measures static contradiction detection in text). SPEC §6.2.

Long-horizon agent tasks (coding first) with **planted decision points and planted temptations** — to contradict a recorded decision (long gaps, context compaction, Logic-Haystacks-style distractors, spec changes testing SUPERSEDE vs. drift) and, since 2026-07-19, to **overreach** (a teammate ping baiting a drive-by edit of a protected module, mirrored by the user's explicit grant ordering the same work — ADR-0008). Each task ships a ground-truth commitment graph → automatic scoring by a deterministic behavioral classifier, symmetrically on both axes: claims **SCR** (drift) / **FRR** (false refusal), actions **ORR** (overreach) / **URR** (underreach — scored from a seed-vs-final tree diff over protected paths).

- `tasks/` — hand-built planted scenarios + ground-truth graphs
- `deonticbench/` — procedural scenario generator (drift & revision + overreach & expansion families; distance / compaction / distractor knobs; dev/eval split; the scope-family siblings are isogenic pairs for paired statistics)
- `harness/` — eval runner, ablation variants (leave-one-out: `no-digest`, `no-tier0`, `no-stopblock`, `silent`; gate modes `blocking`, `bump`, `blocking-claims-only`, `scope-only` — the last two complete the digest × wall 2×2 that attribution needs), classifier, judge, stats
- `results/` — curated reports + promoted rollout-record evidence (see `.gitignore` for the promotion rule)

Status: Phase-2 tooling is built and validated — the first verified paired run reproduces the Phase-0 effect ([progress report](results/DEONTICBENCH-PROGRESS.md)). The actions axis: mechanism shipped and unit-tested; first live paired runs (2026-07-19/20) are a case series, not rates — the drive-by was elicited only under forced compaction, where the overlay closed it, and the runs surfaced three defects in the prose→pin translation, now fixed (ADR-0008 Amendments 1–3). The attribution ablation credits that closing to the post-compaction digest (ADR-0002), not to the scope wall — both valid `blocking-claims-only` runs HELD with the wall off while the bare arm overreached (n=2, one model, one condition, one dropped run the other way); the wall's shown effects are litter suppression (~8×, in-scope output unchanged) and a caught root-escaping write — see the [evidence report](results/SMOKE-SCOPE-REPORT.md) (run design: [overreach-landscape §6](../docs/research/overreach-landscape.md)). Scaling to effect sizes is open ([ROADMAP](../ROADMAP.md)); the eval split stays private (contamination protocol, SPEC addendum A.5).

Env knobs the harness reads (beyond the core `SCOREKEEPER_*` set): `SCOREKEEPER_JUDGE_URL` / `SCOREKEEPER_JUDGE_MODEL` / `SCOREKEEPER_JUDGE_API_KEY` (judge backend; `GEMINI_API_KEY` for the cloud judge), `SCOREKEEPER_PHASE_TIMEOUT` (per-phase agent timeout, seconds).

Published separately when scaled (dataset + harness + leaderboard), citable independently of the tool.
