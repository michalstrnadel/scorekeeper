# arXiv technical report — working outline

**Working title (candidates ranked):**
1. *No Bluffing, No Barging: A Deontic Scoreboard for What LLM Agents May Say and Do*
2. *The Two Failures of Entitlement: Commitment Drift and Scope Overreach in Long-Horizon Agents*
3. *From Advice to Physics: Enforcing Entitlement Semantics in LLM Agents via Brandomian Scorekeeping*
4. *Keeping Score: A Normative Overlay and a Symmetric Benchmark for Commitment Drift in LLM Agents*

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
- Two failure directions, one structure: agents **bluff** (claim without
  entitlement — drift, hallucination) and **barge** (act without entitlement —
  overreach, unrequested work). The 2026 overreach literature (OverEager-Bench
  consent-strip; SNARE harness-dominance; FixedBench action bias) documents
  the second at scale; nobody keys enforcement on *entitlement*.
- Contributions: (1) scorekeeper — an open-source normative overlay (Brandom's
  GOGAR: doxastic *and practical* commitments/entitlements) for agent
  harnesses (hooks + MCP), with two board-adjudicated Tier-0 walls: rival
  claims (ADR-0007) and write scope (ADR-0008, entitlement-keyed `path:`
  pins); (2) DeonticBench — a procedural benchmark measuring the entitlement
  boundary *symmetrically on both axes*: claims (SCR: drift; FRR: false
  refusals — measured) and actions (ORR: overreach; URR: underreach —
  mechanism and instrument shipped; paired runs forthcoming), scored by a
  deterministic artifact-level classifier; (3) an empirically-driven
  escalation of steering channels: advisory context → one-shot speed bump →
  board-adjudicated wall, with each step motivated by a measured failure of
  the previous one.

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
- **Overreach family (the actions axis, ADR-0008):** phase 1 grants a write
  scope (path pins); the final phase pairs a real in-scope task with a
  teammate ping baiting a drive-by cleanup of a protected module (overreach;
  correct = HELD) — mirrored by an explicit user grant ordering the same work
  (expansion; correct = EXECUTED). Metrics ORR/URR (first-use terminology
  disambiguation vs. over-refusal literature). Scored deterministically from
  a seed-vs-final tree diff on the protected paths — no LLM judge; empty diff
  is never HELD (task-success precondition, SNARE-style). The sibling pairs
  are isogenic (shared RNG stream, only the final utterance differs) —
  OverEager-Gen's paired design, licensing paired statistics. Degenerate
  policies are bounded by the pair: do-nothing → URR 100%, do-everything →
  ORR high (AgentAbstain's Paired-Accuracy bound, direction preserved).
  Evidence status stated exactly: mechanism shipped and unit-tested;
  instrument ready; live paired runs pending — no rates implied until they
  land.
- Run-design commitments for the actions-axis ablation (bare vs
  claims-only vs full): fixed allocation, average-rate aggregation, GEE /
  cluster-aware inference, cluster bootstrap by scenario; budget anchor ≈36
  paired scenarios × 3 runs × 2 arms (research/overreach-landscape.md §6).
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
6. [Overreach family — mechanism verified by unit/chain tests (scope wall:
   deny → wall → entitled grant → pass, across real process boundaries);
   live A/B numbers to be inserted when paired runs land; nothing reported
   before then.]

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
- **The boundary lives on the board, not in the prompt:** OverEager-Bench's
  consent-strip (0.0%→17.1% when the scope sentence is removed, with agents
  pattern-matching the declaration text) shows a prompt-borne scope boundary
  evaporates with the prompt — after compaction, after a subagent hop. A
  scope grant recorded as a commitment is compaction-proof, provenanced, and
  supersedable through the same entitled-revision flow the FRR probe already
  priced at zero denies. SNARE's variance decomposition (harness 56% vs base
  model 21%) locates the leverage at exactly this layer. And the tempting
  alternative — dependency-graph *auto*-widening of scope — reintroduces the
  Progent-class mid-run policy-loosening hole; board adjudication is the
  judge–optimizer separation answer (cf. §5 protected-grader ¶).
- Legibility even in failure: when drift succeeds (Bash bypass, extraction
  errors), the board still records it — auditability as the floor, prevention
  as the ceiling.
- Limitations: lexicon precision/recall (camouflaged drivers), Bash-write
  bypass (both walls), small n, single agent model family so far, extraction
  quality as a separate axis (false SUPERSEDE events); scope pins enter via
  seeding/MCP/user in v1 — extractor-proposed `path:` pins are future work;
  effort-proportionality reserved (Diff-XYZ churn buckets as the
  deterministic proxy).

## 6. Call to community

- 60-second install (plugin), experience-report issue template, DeonticBench
  run instructions; leaderboard intent.

## Appendix

- ADR index; classifier marker tables; full run manifests; reproduction
  commands (deterministic generator seeds).
