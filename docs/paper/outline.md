# arXiv technical report — working outline

**Working title (candidates ranked):**
1. *From Advice to Physics: Enforcing Entitlement Semantics in LLM Agents via Brandomian Scorekeeping*
2. *The Entitlement Boundary: Distinguishing User Directives from Agent Inferences in Long-Horizon Execution*
3. *Keeping Score: A Normative Overlay and a Symmetric Benchmark for Commitment Drift in LLM Agents*

**Format:** arXiv cs.AI / cs.MA technical report, 8–12 pages incl. appendix.
**Artifacts:** scorekeeper (PyPI, plugin, MCP) + DeonticBench + all run evidence.
**Tone rule:** every claim anchored to a run artifact or a test; the honest
negative results ARE the story, not a footnote. Novelty phrasing strictly per
[docs/research/related-work.md](../research/related-work.md) — no absolute
"nothing else does this" claims.

## 1. Introduction

- Long-horizon agents drift: they revise their own recorded decisions without
  authority — additive drift with camouflage included (live example: docstring
  says "backed by Redis", import says pymemcache).
- The missing primitive is not memory but **normative state**: who was
  *entitled* to change a commitment. User-ordered supersede ≠ agent-inferred
  revision, even when the diff is identical.
- Contributions: (1) scorekeeper — an open-source normative overlay (Brandom's
  GOGAR: commitments/entitlements) for agent harnesses (hooks + MCP);
  (2) DeonticBench — a procedural benchmark measuring the entitlement boundary
  *symmetrically* (SCR: drift; FRR: false refusals), scored by a deterministic
  artifact-level classifier; (3) an empirically-driven escalation of steering
  channels: advisory context → one-shot speed bump → board-adjudicated wall,
  with each step motivated by a measured failure of the previous one.

## 2. Framework: deontic scoreboard (theory.md distilled)

- Commitment / entitlement / incompatibility; SUPERSEDE vs BRANCH-CONFLICT as
  *the same edit with different provenance*.
- Architecture: extraction on Stop (async), digest re-injection (compaction
  survival), Tier-0 content scan (ms, lexicon), Tier-1 material check, the
  gate (ADR-0007). Scaffolded-not-extended stance: the agent has no write
  authority over its own scoreboard.
- Related work positioning (from related-work.md): AGM entrenchment, ManyIH
  privilege tiers, Akrasia, AOIA-Core, Zep — the three-part delta.

## 3. DeonticBench

- Procedural generator: worlds × tech pairs × distance × forced compaction ×
  distractors; dev/eval RNG split, contamination protocol (generated/ never
  committed). **Naming note:** renamed from the working name "EntitleBench"
  (collision with the established commit-message benchmark).
- Mirror families: drift (unentitled temptation; correct = HELD) and revision
  (entitled order; correct = EXECUTED). Symmetric metrics: SCR and FRR.
- Deterministic behavioral classifier as primary metric; LLM judge demoted to
  secondary after measured degeneracy (all-1s verdicts, timeouts). Classifier
  itself adversarially hardened: 33-agent review + live-run audits; every
  confirmed misfire is a regression test anchored on a verbatim reply.

## 4. Results: the escalation story (all n small — framed as case series, not rates)

1. **Phase 0** (planted scenario, n=6+6): bare drifted 1/6, scorekept 0/6,
   FPR 0, +0.6 % tokens. Mechanism works end-to-end.
2. **Seed-0 paired smoke** (hardest condition, d8cx): pg-mongo reproduces the
   effect (bare DRIFTED via pymongo in code / scorekept HELD, gated on
   confirmation). **Negative finding #1:** redis pair — scorekept drifted
   *additively* past 11 advisory warnings ("polyglot" rationalization); the
   extractor recorded the drift itself onto the board.
3. **Gate v1 (speed bump) A/B:** deny fired; **negative finding #2:** the
   agent lifted the bump by *self-attesting* entitlement (claimed the pasted
   draft note as the user's order), shipped the drift; false SUPERSEDE landed
   (must_not_fire tripped).
4. **Gate v2 (board-adjudicated wall):** deny stands until the scoreboard
   records an entitled SUPERSEDE through the operator pipeline. Live smoke:
   wall held under forced attempts; agent surfaced and deferred per
   instructions. A/B on the same failed scenario (run-20260714T094753):
   **HELD/high — 2 denies, zero rival code landed, the final reply surfaced
   the conflict.** FRR probe on the revision family (run-20260714T103947):
   **EXECUTED/high with ZERO denies** — turn-end extraction recorded the
   user-ordered supersede before any rival write was attempted, so the
   entitled path cost nothing (expected SUPERSEDE event hit, no false
   events); wall-time overhead ~41 % vs. advisory scorekept on the drift run.
5. Cross-reference: Recuse-Signal findings (small models comply with hard
   in-band denials; frontier models reweigh authority) — our results extend
   this: *soft* denials with self-attested escapes are exploitable by small
   models too; the adjudicator must be external state, not the model.

## 5. Discussion

- Advice vs. physics: prompts address the driver, the environment addresses
  the road; entitlement must live out-of-process.
- **The gate as a protected grader** (cf. Karpathy's `train.py`/`prepare.py`
  split; [self-improvement-landscape](../research/self-improvement-landscape.md)):
  negative finding #2 — the agent lifting the bump by self-attesting
  entitlement — is an in-vivo instance of the verifier-gaming failure the
  Darwin Gödel Machine authors documented (the agent disabled its own
  hallucination detector, arXiv:2505.22954). The board-adjudicated wall is
  judge–optimizer separation for normative state (cf. Red Queen GM,
  arXiv:2606.26294); our escalation story independently reproduces, at the
  scale of one commitment, the trajectory the self-improvement field walked
  at the scale of whole benchmarks. Corollary for self-improving agents: a
  loop that edits its own harness needs exactly a commitment ledger outside
  its write authority; the audit trail doubles as the hard-versioned
  modification history that self-modifying deployments will need for
  oversight (EU AI Act Art. 14 analysis — inference, not settled guidance).
- Legibility even in failure: when drift succeeds (Bash bypass, extraction
  errors), the board still records it — auditability as the floor, prevention
  as the ceiling.
- Limitations: lexicon precision/recall (camouflaged drivers), Bash-write
  bypass, small n, single agent model family so far, extraction quality as a
  separate axis (false SUPERSEDE events).

## 6. Call to community

- 60-second install (plugin), experience-report issue template, DeonticBench
  run instructions; leaderboard intent.

## Appendix

- ADR index; classifier marker tables; full run manifests; reproduction
  commands (deterministic generator seeds).
