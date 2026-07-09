# Rollout Cards (Addendum-1 §A.4)

Reporting rules can move scores by ~20 p.b.; every published number therefore ships
as a three-part, versioned package:

1. **Rollout record** — `results/run-<stamp>/results.json`: per phase the full user
   prompt, tool calls, raw agent reply, token usage and wall time; for scorekept
   runs additionally the complete `.scorekeeper` audit log (`scoreboard_log`).
2. **Views** — the code that extracts what is judged: `judge.py`
   (`build_trajectory_record`, `strip_style`, rubric), `run.py::collect_files` and
   `run.py::score_events`. Versioned in git; a published number references the
   commit hash.
3. **Reporting rules + drops manifest** — aggregation lives in `run.py::summarize`
   and `stats.py` (Wilson for binary, smooth bootstrap for continuous, clustered SE,
   P90/P99 latency). Every run with a non-empty `error` is a declared drop, listed
   in the summary's *Drops manifest* section — no silent exclusions.

Gate: the full matrix must not run before `meta_eval.py` reports CV ≤ 0.05
(`results/meta-eval.json`; deviation for unseedable agent sampling: QUESTIONS Q9).
