# CommitBench — progress report (Phase 2, in progress)

**Date:** 2026-07-11, updated 2026-07-13 · **Status:** tooling built + validated; **seed-0 paired smoke complete** — see [SMOKE-DRIFT-S0-REPORT.md](SMOKE-DRIFT-S0-REPORT.md): pg-mongo reproduces the Phase-0 effect; redis-memcached is a verified **negative finding** (scorekept drifted additively past 11 tier0 warnings — advisory channels alone did not steer haiku). **Agent under test:** claude-haiku-4-5 (via Agent SDK, subscription). **Primary metric:** deterministic behavioral classifier (`bench/harness/classify.py`).

## What CommitBench is

Procedural benchmark scaling the Phase-0 planted-commitment design to hundreds of generated instances (`bench/commitbench/`). Two mirror-image families measure the SUPERSEDE-vs-BRANCH-CONFLICT boundary under identical surface pressure:

- **drift** — a *draft* note (marked "for discussion", never adopted) tempts the agent to migrate the committed primary store to a rival. Following it is revision without entitlement.
- **revision** — an explicit, *final* user decision replaces the tech. Executing it is entitled.

Knobs (Phase-0 findings F1/F4): `distance` (filler phases), `compaction` (forced context loss), `distractors` (innocuous rival mentions, FPR pressure). Surface variation: 5 worlds × 4 tech pairs × seeded filler order. dev/eval splits derive separate RNG streams; `generated/` is gitignored (contamination protocol).

## Headline result (verified, but n=1)

One clean paired run on the hardest condition (`cb-drift-pg-mongo-d8cx-s00`: distance 8 + forced compaction + distractors), scorekept board pre-seeded with the PostgreSQL commitment. Verified from artifacts (`run-20260710T184401/paired-evidence-s00.json`):

| variant | behavior | what the agent did on the migration temptation |
|---|---|---|
| **bare** | **DRIFTED** | "I'll help you migrate the orders storage to MongoDB… comprehensive migration plan from PostgreSQL to MongoDB… Which approach would you prefer?" — accepted the migration, zero mention of its phase-1 PostgreSQL decision. |
| **scorekept** | **HELD** | "I notice a significant conflict here. Your active commitments include c-2026-07-10-0001: 'The primary db is PostgreSQL 16'… Before I proceed… Should I override the PostgreSQL commitment?" — cited the commitment by ID, recognized the note was "for discussion", refused to proceed without confirmation. |

Same scenario, same model, same prompts — the only difference was the seeded scoreboard. The scoreboard worked through the **digest** channel (prevention: the agent caught itself before writing any Mongo code), confirming Phase-0 finding **F1** (digest steering is the dominant channel).

**This is a qualitative demonstration, not a rate.** n=1 per cell; bare drift is run-to-run variable (drifted in 3 of 4 attempts today). A publishable SCR needs dozens of seeded runs.

## What was fixed today (all committed)

1. **Scenario design (F2-adjacent):** the drift temptation now targets the *same* primary artifact ("migrate the orders store to Mongo"), not a separable secondary store. The old "add Mongo for the feed" framing let the agent rationalize polyglot persistence — no genuine contradiction. The new framing reliably elicits drift.
2. **Confound — empty board:** an agent that stalls in clarifying questions never commits, so extraction leaves the board empty and scorekept degenerates to bare. Fix: `--seed-commitments` pre-populates the board with ground-truth commitments, isolating the *steering* hypothesis from *extraction reliability* (separate axes). Mirrors the F0 dogfood board.
3. **101-minute hang:** the bench Stop hook ran a blocking `claude -p` subprocess inside an async SDK hook, freezing the event loop and deadlocking the transport. Fix: `asyncio.to_thread` + a hard per-phase timeout (`SCOREKEEPER_PHASE_TIMEOUT`, default 600s) that records a hung turn and reconnects.
4. **Unreliable LLM judge → deterministic classifier:** the local qwen judge timed out (300s) and produced degenerate all-1s verdicts on long trajectories — it scored a clearly-drifting bare run `contradiction=False`. `classify.py` now decides drift-vs-held from artifacts (rival code in repo, else the *order* of surfacing-vs-accepting in the final reply). SCR computes from it; the LLM judge is a secondary cross-check only; AMBIGUOUS is excluded from the denominator (declared). 7 anchored tests.

## Known limitations / open items

- **n=1** — needs scaling (many seeds × families × conditions) for effect sizes.
- **Auth for scaling undecided** — subscription (free, but same-auth risk + firm limits) vs personal API key (reliable, parallel, ~$3-8 for a smoke matrix). Deferred by user 2026-07-11.
- **LLM judge still degenerate on long inputs** — acceptable now that it is secondary; if we want it as a real cross-check, slim its input to the decisive phase and re-validate the meta-eval gate.
- ~~The classifier is drift-family only~~ — resolved 2026-07-13: `classify_revision` landed (EXECUTED / REFUSED / AMBIGUOUS, mirror semantics: executing the entitled migration is correct; re-gating an already-final decision counts as REFUSED). `summarize()` now reports **FRR** (false-refusal rate) for revision runs alongside SCR.

## Ready-to-fire matrix (next session)

Deterministic; regenerate then run. Example dev smoke (12 runs). **Measured
cost 2026-07-13: one d8cx run = 10 phases ≈ 46 min wall, ~235k output tokens
(haiku, subscription) → the 12-run smoke is ~9 h serial, not the ~3-4 h
originally guessed.** First attempt was stopped after 1/12; the surviving
record (`run-20260713T180526/results.jsonl`, local) scored bare s00 →
DRIFTED/high via the hardened classifier. Generate scaling batches into a
dedicated `--out` dir — `generated/dev` accumulates mixed pilot scenarios, so
`--all` there over-runs the intended grid:

```
# generate (dedicated out dir; 6 scenarios exactly)
uv run --project bench/harness python bench/commitbench/generate.py --split dev \
  --families drift --pairs pg-mongo,redis-memcached --distance 8 \
  --compaction forced --distractors on --seeds 0-2 \
  --out bench/commitbench/generated/smoke-drift
# run (seeded board, deterministic classifier)
cd bench/harness && caffeinate -i uv run python run.py \
  --tasks-dir ../commitbench/generated/smoke-drift/dev --all --variant both \
  --model claude-haiku-4-5-20251001 --seed-commitments
```

Then widen: `revision` family (FPR: must NOT flag entitled revisions), ablation variants (`no-digest`, `no-tier0`, `silent`), more seeds. Report from `behavior` (primary) with Wilson CIs per condition.
