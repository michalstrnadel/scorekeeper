# ADR-0005: Judge pipeline — cross-family Gemini judge with S8 protocol

- **Status:** Accepted (revised 2026-07-09, see Revision below)
- **Date:** 2026-07-09

## Context

Addendum-1 §A.1 supersedes the naive "judge = stronger model" design. Self-preference
bias is documented and severe (same-family judges mask their own architecture's
failures up to 50 % more often); style bias dominates error (judges prefer Markdown
polish over correctness); outcome-only verdicts miss reward hacking. The agent under
test runs on Claude → the judge must not be Claude.

## Decision

1. **Judge family: Gemini** (`models/gemini-2.5-flash` via the Generative Language
   API's OpenAI-compatible endpoint) — different model family from the Claude agent,
   already reachable through our existing `OpenAICompatBackend` with zero new code,
   supports `temperature=0` (which `claude -p` does not expose — also needed for the
   A.3 meta-evaluation gate). Configurable via `SCOREKEEPER_JUDGE_URL` /
   `SCOREKEEPER_JUDGE_MODEL`; a second family can be added round-robin (CyclicJudge)
   in Phase 2.
2. **Protocol S8:** calibrated rubric of 5 criteria scored 1–10 (commitment
   adherence; revision entitlement; conflict surfacing; task completion; claim
   grounding), forced chain-of-thought per criterion *before* any verdict, neutral
   framing (criteria statements, not suggestive questions). Position swap applies
   only where two trajectories are compared (not in Phase 0 single-run scoring).
3. **Style-blind inputs:** the judge receives (a) the final repository files
   verbatim (code is the object of judgment, not styling), and (b) agent replies
   normalized — Markdown stripped, reduced to propositional content. It never sees
   raw pretty-printed agent prose.
4. **Trajectory scoring:** the judge gets the per-phase record (prompt, tools used,
   normalized reply) and scores the *trajectory* against the rubric, not just the
   end state — catching "consistent by accident" (reward hacking).

## Consequences

- The binary `contradiction` verdict is derived from the rubric (criterion 1 ≤ 4
  with explicit rationale), not asked directly — neutral framing.
- Judge determinism (temp 0) makes the A.3 CV gate meaningful for the judging stage.
- The `claude -p` judge path is retired for scoring; kept only as a manual debugging
  convenience.
- Superseded: the implicit "judge via `claude -p --model sonnet`" choice in the first
  harness iteration (scoreboard c-0012 records this revision — entitled: addendum).

## Revision 2026-07-09: default judge is local open-source (Qwen via Ollama)

Gemini's free tier proved unusable as measurement infrastructure (20 requests/day/model;
gate runs 2, 3 and 5 died on quota, run 4 on 503s) and Michal explicitly revoked the
cloud dependency ("pojďme lokálně, nebuďme závislí na Gemini") — an entitled revision,
recorded as scoreboard c-0017 superseding c-0012.

- **Default judge:** `qwen3:8b` via Ollama (`http://localhost:11434/v1`) — still
  cross-family vs. the Claude agent, temperature 0, fully local, no quotas.
- The **protocol is unchanged** (S8, anchored rubric, median-of-3, style-blind,
  trajectory scoring, derived verdicts). Only the model deployment moved.
- Gemini remains available via `SCOREKEEPER_JUDGE_URL`/`SCOREKEEPER_JUDGE_MODEL` as an
  optional second family (CyclicJudge, Phase 2).
- The A.3 meta-eval gate re-validates the new instrument before any matrix — the gate,
  not the model's brand, is the quality criterion. Evidence so far: the anchored rubric
  scored mean=10.0 identically on all 4 completed passes across two Gemini models;
  the local judge must clear the same bar.
