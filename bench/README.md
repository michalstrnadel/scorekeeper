# CommitBench

Benchmark for an agent's consistency with its **own** commitments — the gap no existing benchmark fills (BeliefShift measures consistency with the *user's* beliefs; Logic Haystacks measures static contradiction detection in text). SPEC §6.2.

Long-horizon agent tasks (coding first) with **planted decision points and planted temptations to contradict** (long gaps, context compaction between decision and temptation, Logic-Haystacks-style distractors, spec changes that test SUPERSEDE vs. drift). Each task ships a ground-truth commitment graph → automatic SCR / JRR scoring.

- `tasks/` — task definitions + ground-truth graphs
- `harness/` — eval runner, ablations, scoring

Published separately (dataset + harness + leaderboard), citable independently of the tool. Not implemented yet — Phase 2.
