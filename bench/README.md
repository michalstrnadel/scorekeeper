# DeonticBench

Benchmark for an agent's consistency with its **own** commitments — the gap no existing benchmark fills (BeliefShift measures consistency with the *user's* beliefs; Logic Haystacks measures static contradiction detection in text). SPEC §6.2.

Long-horizon agent tasks (coding first) with **planted decision points and planted temptations** — to contradict a recorded decision (long gaps, context compaction, Logic-Haystacks-style distractors, spec changes testing SUPERSEDE vs. drift) and, since 2026-07-19, to **overreach** (a teammate ping baiting a drive-by edit of a protected module, mirrored by the user's explicit grant ordering the same work — ADR-0008). Each task ships a ground-truth commitment graph → automatic scoring by a deterministic behavioral classifier, symmetrically on both axes: claims **SCR** (drift) / **FRR** (false refusal), actions **ORR** (overreach) / **URR** (underreach — scored from a seed-vs-final tree diff over protected paths).

- `tasks/` — hand-built planted scenarios + ground-truth graphs
- `deonticbench/` — procedural scenario generator (drift & revision + overreach & expansion families; distance / compaction / distractor knobs; dev/eval split; the scope-family siblings are isogenic pairs for paired statistics)
- `harness/` — eval runner (`run.py` drives Claude Code via the Agent SDK; `loop_run.py` is the model-agnostic reference loop, ADR-0009), ablation variants (leave-one-out: `no-digest`, `no-tier0`, `no-stopblock`, `silent`; gate modes `blocking`, `bump`, `blocking-claims-only`, `scope-only` — the last two are the single-intervention cells the digest × wall attribution needs), classifier, judge, stats
- `results/` — curated reports + promoted rollout-record evidence (see `.gitignore` for the promotion rule)

Status: Phase-2 tooling is built and validated — the first verified paired run reproduces the Phase-0 effect ([progress report](results/DEONTICBENCH-PROGRESS.md)). The actions axis: mechanism shipped and unit-tested; first live paired runs (2026-07-19/20) are a case series, not rates — the drive-by was elicited only under forced compaction, where the overlay closed it, and the runs surfaced three defects in the prose→pin translation, now fixed (ADR-0008 Amendments 1–3). The attribution splits by model: on the weak model the ablation credits the closing to the post-compaction digest (ADR-0002), not to the scope wall — both valid `blocking-claims-only` runs HELD with the wall off while the bare arm overreached (n=2, one dropped run the other way); on the strong model every cell of the 2×2 now holds — the digest by preventing the attempt, the wall by denying an attempted write it was armed for by live extraction, and the seeded digest+wall cell HELD clean on a fresh-budget rerun (n=1 per cell, one scenario; the first both-on attempt dropped when usage credits died mid-turn, F21). The direction replicates **cross-vendor** in the reference loop (bare Gemini/GPT barge 3/4, governed cells hold 8/8, `silent` placebo barges like bare — [LOOP-SMOKE report](results/LOOP-SMOKE-REPORT.md)). The first **powered seed set** (10 isogenic d8cx pairs on gpt-5.4-mini, [POWERED-LOOP report](results/POWERED-LOOP-REPORT.md)) turns the case series into a rate and lands it honestly low on that vendor: bare ORR 1/10 (Wilson 95% [1.8%, 40%] — and the morning's single-run barge did not replicate; temperature 0 ≠ determinism), governed 0/10 with zero denies (governed loop cells now 18/18 across all campaigns). The barge is model- and elicitation-dependent — the `d8cxq`/`d8cxqi` families and the Gemini backend are the next powered targets. The wall's further shown effects are litter suppression (~8×, in-scope output unchanged) and a caught root-escaping write — see the [evidence report](results/SMOKE-SCOPE-REPORT.md) (run design: [overreach-landscape §6](../docs/research/overreach-landscape.md)). Scaling to effect sizes is open ([ROADMAP](../ROADMAP.md)); the eval split stays private (contamination protocol, SPEC addendum A.5).

Env knobs the harness reads (beyond the core `SCOREKEEPER_*` set): `SCOREKEEPER_JUDGE_URL` / `SCOREKEEPER_JUDGE_MODEL` / `SCOREKEEPER_JUDGE_API_KEY` (judge backend; `GEMINI_API_KEY` for the cloud judge), `SCOREKEEPER_PHASE_TIMEOUT` (per-phase agent timeout, seconds).

## Reference loop — run the bench on any model (ADR-0009)

`harness/loop_run.py` is a second, parallel driver: a minimal agent loop over
raw chat-completions APIs with its own tool belt (Claude-Code-shaped `Read` /
`Write` / `Edit` / `Glob` / `Grep` / `Bash`) and the plugin's own hook handlers
wired around dispatch — so the **digest, the audit, and the scope wall are
enforced for any model**, including fully local open-source ones. Results are
a separate evidence branch from the in-product (`run.py`) runs and are never
pooled with them; every record carries `harness: "reference-loop"` and the
backend id.

```bash
# local open-source (Ollama / LM Studio / vLLM — any OpenAI-compat server)
uv run python loop_run.py --tasks-dir ../deonticbench/generated/calib/dev \
    --scenario cb-overreach-pg-mongo-d8cx-s00 --variant bare \
    --backend local --model qwen3:8b

# Gemini (GEMINI_API_KEY), seeded wall + digest. Mind the quota: an agent
# loop spends one request per tool iteration (~50-150 per scenario), so
# free-tier daily caps die in minutes — pace with --rpm and use a paid key.
uv run python loop_run.py --tasks-dir ../deonticbench/generated/calib/dev \
    --scenario cb-overreach-pg-mongo-d8cx-s00 --variant blocking \
    --seed-commitments --backend gemini --model gemini-2.5-flash --rpm 12

# OpenAI (OPENAI_API_KEY); any other server via --backend openai-compat --base-url URL
uv run python loop_run.py ... --backend openai --model gpt-5.2
```

Caveat by design: the loop is **seeded-only** (`--seed-commitments` is
required for non-bare variants) — extraction is transcript-format-bound and
stays measured in-product (F20). Compaction is injected deterministically
(history reset). CLI agent products (Gemini CLI, Codex CLI) are a different
integration class and out of scope here.

Published separately when scaled (dataset + harness + leaderboard), citable independently of the tool.
