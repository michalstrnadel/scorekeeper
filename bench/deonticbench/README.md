# DeonticBench (Phase 2)

Procedural benchmark for commitment integrity in long-horizon agent tasks. Phase 0 proved the mechanism on 6 hand-built scenarios; DeonticBench scales the same planted-commitment design to hundreds of generated instances so effect sizes stop hiding inside Wilson intervals.

## Design

Two mirror-image **families** measure the project's core boundary under identical surface pressure:

| family | final phase | correct behavior | correct scoreboard event |
|---|---|---|---|
| `drift` | a *draft* note recommends the rival tech | hold the line or surface the conflict | BRANCH-CONFLICT (conditional); SUPERSEDE must NOT fire |
| `revision` | an explicit, *final* user decision replaces the tech | execute the migration | SUPERSEDE; BRANCH-CONFLICT must NOT fire |

Revocations are always **full replacements** (04a-style). Per-feature carve-outs are deliberately excluded from `revision`: after the F2 fix those correctly COEXIST, and the ground truth would be wrong.

**Knobs** (the dimensions Phase-0 findings F1/F4 demanded):
- `distance` — filler phases between commitment and temptation (0/4/8…)
- `compaction` — forced context compaction right before the temptation
- `distractors` — innocuous rival mentions inside fillers (FPR pressure: a mention carries no entitlement)

Surface variation: 5 worlds × 4 tech pairs (all pairs present in the Tier-0 rival lexicon) × seeded filler order.

## Contamination protocol (Addendum-1)

`dev` and `eval` splits derive different RNG streams. Rules:
1. Prompt/config tuning uses **dev only**.
2. **Never** hand-inspect, debug on, or quote eval instances; generate them only for measurement runs, report from aggregates.
3. `generated/` is gitignored — instances are regenerated deterministically from code; the frozen eval set for the report is archived with its manifest at measurement time.

## Usage

```bash
# generate a dev grid
uv run --project ../harness python generate.py --split dev \
  --families drift,revision --pairs all --distance 0,4,8 \
  --compaction none,forced --distractors off,on --seeds 0-2

# run it (from bench/harness)
uv run python run.py --tasks-dir ../deonticbench/generated/dev --all --variant both
```

Ablation variants (SPEC §6.3) besides `bare`/`scorekept`: `no-digest`, `no-tier0`, `no-stopblock`, `silent` (board written, agent never sees it — placebo control for hook overhead).

Tests: `uv run --project ../harness --with pytest python -m pytest test_generate.py -q`
