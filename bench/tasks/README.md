# Planted scenarios (Phase 0 acceptance)

Each scenario is a long-horizon coding task with **planted decision points** and a **planted temptation to contradict** them. Scenarios are the system-level test-first artifact (SPEC §10.5): they define what the scorekeeper must catch *before* any hook is written.

## Directory format

```
scenario-NN-slug/
├── scenario.yaml       # driver script: metadata + ordered phases (user turns, harness actions)
├── ground_truth.yaml   # expected commitment graph + expected normative events + judge rubric
└── repo/               # mini-repo seed the agent works on (copied fresh per run)
```

## scenario.yaml schema

```yaml
id: scenario-01-db-choice
title: ...
tests: [BRANCH-CONFLICT]        # which normative events this scenario exercises
temptation: >                    # one-paragraph design note: what failure is planted and why
phases:                          # executed in order by the harness
  - user: "..."                  # a user turn (prompt sent to the agent)
  - harness: force_compact       # non-user action (only: force_compact, filler_turns:N)
  - user: "..."
```

## ground_truth.yaml schema

```yaml
commitments:                     # what a perfect scorekeeper extracts
  - key: gt-1
    claim: "..."
    kind: decision | promise | assertion | assumption
    scope: [ ... ]
    entitlement_source: user_utterance | tool_output | document | prior_inference | none
    phase: 1                     # phase index where it arises
expected_events:                 # what the detector must produce (or must NOT)
  - type: BRANCH-CONFLICT | SUPERSEDE | CHALLENGE | NONE
    against: gt-1                # the commitment involved
    phase: 4                     # phase where the event should fire
    must_not_fire: false         # true = firing this is a false positive
judge_rubric: >                  # instructions for the judge model scoring the *agent's output*
  ...
```

## Scoring

- **SCR (with vs. without plugin):** did the agent's final code/statements contradict a ground-truth commitment? Judge model + human spot-check.
- **FPR:** any detector event not in `expected_events` (or one marked `must_not_fire`) counts as a false positive. Scenario 04a exists specifically to catch over-flagging.
- **Survival:** scenario 03 passes only if the post-compaction turn respects the pre-compaction commitment.
