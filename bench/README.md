# DeonticBench

Benchmark for an agent's consistency with its **own** commitments — the gap no existing benchmark fills (BeliefShift measures consistency with the *user's* beliefs; Logic Haystacks measures static contradiction detection in text). SPEC §6.2.

Long-horizon agent tasks (coding first) with **planted decision points and planted temptations to contradict** (long gaps, context compaction between decision and temptation, Logic-Haystacks-style distractors, spec changes that test SUPERSEDE vs. drift). Each task ships a ground-truth commitment graph → automatic **SCR** (scorekeeping-consistency) and **FRR** (false-refusal) scoring by a deterministic behavioral classifier.

- `tasks/` — hand-built planted scenarios + ground-truth graphs
- `deonticbench/` — procedural scenario generator (drift & revision families; distance / compaction / distractor knobs; dev/eval split)
- `harness/` — eval runner, ablation variants (leave-one-out: `no-digest`, `no-tier0`, `no-stopblock`, `silent`; gate modes `blocking`, `bump`), classifier, judge, stats
- `results/` — curated reports + promoted rollout-record evidence (see `.gitignore` for the promotion rule)

Status: Phase-2 tooling is built and validated — the first verified paired run reproduces the Phase-0 effect ([progress report](results/DEONTICBENCH-PROGRESS.md)). Scaling to effect sizes is open ([ROADMAP](../ROADMAP.md)); the eval split stays private (contamination protocol, SPEC addendum A.5).

Env knobs the harness reads (beyond the core `SCOREKEEPER_*` set): `SCOREKEEPER_JUDGE_URL` / `SCOREKEEPER_JUDGE_MODEL` / `SCOREKEEPER_JUDGE_API_KEY` (judge backend; `GEMINI_API_KEY` for the cloud judge), `SCOREKEEPER_PHASE_TIMEOUT` (per-phase agent timeout, seconds).

Published separately when scaled (dataset + harness + leaderboard), citable independently of the tool.
