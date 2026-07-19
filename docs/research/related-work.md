# Related work & positioning (curated)

Distilled from a deep-research landscape sweep (2026-07-13, full report:
[landscape-2026-07.md](landscape-2026-07.md)), extended 2026-07-19 with the
action-axis sweep ([overreach-landscape.md](overreach-landscape.md)). This is
the working related-work section for the paper and the source of truth for how
we phrase novelty claims.

## The honest novelty statement

**Do not claim** "nothing tracks the user-ordered vs. agent-inferred boundary."
That absolute claim is refuted by at least three lines of work:

- **AGM belief revision systems** (MnemeBrain, XTrace): *entrenchment* protects
  user-curated axioms from system inference, and they distinguish retraction
  from supersession — functionally close to our entitled/unentitled boundary.
- **Many-Tier Instruction Hierarchy (ManyIH)**: scalar privilege levels per
  instruction source; user prompts outrank the agent's own tool outputs.
- **Provenance-enhanced knowledge graphs (DEC)**: user-asserted facts as
  foundational, agent-derived hypotheses as doxastic.

**Do not claim** "first overreach benchmark" or "first scope enforcement"
either. FixedBench (arXiv:2605.07769) already measures both directions of the
act/abstain boundary; OverEager-Bench (2605.18583), SNARE (2605.28122) and
UnderSpecBench (2607.02294) already measure unrequested/out-of-scope actions;
Progent (2504.11703) and Agent Contracts (2601.08815) already enforce
resource-level restrictions. See
[overreach-landscape.md](overreach-landscape.md).

**Do claim** the three-part delta (each part individually has neighbors; the
combination does not):

1. **Semantic framework** — Brandomian commitments/entitlements (GOGAR)
   operationalized in a live execution loop, not a static entrenchment rule or
   privilege scalar. The scoreboard models the *social mechanics of
   accountability*: assert, challenge, supersede, conflict — over doxastic
   commitments (claims) *and* practical commitments (deeds): entitlement to
   act, not only to claim (theory.md §1b).
2. **Active execution overlay** — the closest systems are passive (memory
   engines, eval suites). Scorekeeper turns the boundary into environmental
   *physics* via hooks + MCP: the blocking Tier-0 gate (ADR-0007) denies the
   first unentitled rival write, and the scope wall (ADR-0008) denies writes
   outside the entitled `path:` grant — both lift only when the board itself
   records an entitled revision. Enforcement is *entitlement-keyed* (who
   granted what, with provenance), not resource-keyed (which files/tools are
   allowed) — the delta vs. Progent-class privilege control.
3. **Symmetric measurement, on both axes** — the benchmark penalizes the
   too-eager failure *and* its too-timid shadow at the same boundary, on both
   axes: claims (SCR: drift / FRR: false refusal) and actions (ORR: overreach
   / URR: underreach), scored by a deterministic artifact-level classifier
   instead of an LLM judge. No surveyed benchmark covers the 2×2 (FixedBench
   is closest: both directions of abstention, but no enforcement overlay and
   no false-restriction cost of one; BMB: storage logic, no live FRR;
   Akrasia: contradiction only; ManyIH-Bench: adherence only).

One-line pitch: **operationalizing social pragmatics as a protocol-level
blocking channel for what the agent may say and do, measured symmetrically on
both axes.**

## The five closest works and the delta

| System | Tracks commitments | Entitlement/provenance | Blocking channel | Benchmark | Delta vs. scorekeeper |
|---|---|---|---|---|---|
| MnemeBrain / XTrace (AGM) | belief states | entrenchment hierarchy | no (memory infra) | BMB (storage logic) | passive store; no live agent FRR/SCR; no execution control |
| ManyIH | instructions, not commitments | scalar privilege | no (eval framework) | ManyIH-Bench | ranks instructions; doesn't model the agent's own promises or supersede semantics |
| Akrasia bench | internal goals | no | no | goal drift under pressure | measures the failure; offers no runtime mechanism |
| AOIA-Core | provenance chain | evidence vs. reasoning | read-only grammar | audit surfaces | epistemic hygiene for retrieval; no commitment lifecycle, no symmetric eval |
| Zep (Graphiti) | temporal facts | no belief status | no | LoCoMo/LongMemEval | bi-temporal "what was true when"; no *who was entitled to change it* |

## The action axis: closest works and the delta (added 2026-07-19)

| System | Measures/enforces | Symmetric? | Keyed on | Delta vs. scorekeeper |
|---|---|---|---|---|
| OverEager-Bench (2605.18583) | out-of-scope actions on benign tasks; paired consent-strip design (McNemar) | no (eager side only) | prompt scope sentence | measurement only; boundary lives in the prompt (consent-strip: 0.0%→17.1%) — we adopt its isogenic-pair design for the overreach/expansion families |
| SNARE (2605.28122) | overeager elicitation, 10k runs | no | trap predicates | measurement only; its harness-dominance finding (56% vs 21%) argues *for* a harness overlay |
| UnderSpecBench (2607.02294) | OverScope oracle on underspecified DevOps tasks | no | side-effect oracles | measurement only; oracle kin of our protected-path diff; its acted-runs denominator (OSR 31.4%→87.0% conditioned) is a secondary reporting view we note |
| FixedBench (2605.07769) | act-vs-abstain, both directions | **yes** (abstention) | task ground truth | closest neighbor; no enforcement overlay, no cost-of-enforcement metric |
| AgentAbstain (2607.10059) | paired act/abstain accuracy; DAG commit check defeats hallucinated abstention | **yes** (paired) | isogenic task pairs | its Paired Accuracy bounds static do-nothing policies at 0% — the same bound our mirrored family pair provides; no enforcement overlay |
| ClawsBench (2604.05172) | UAR (unsafe actions) vs TSR; composite Safe Completion Rate | partial (composite) | mock-API snapshots | "safe because unable" exposed via composite; NB its "SCR" = Safe Completion Rate, a name collision with our self-contradiction rate |
| Progent (2504.11703) | privilege control over tool calls | no | resources (tool names/args) | enforcement without entitlement provenance; policies loosenable mid-run |
| Agent Contracts (2601.08815) | resource/temporal budget contracts | no | budgets | orchestrator-level; no per-write gate, no deontic ledger |
| Normative MAS (Singh, Castelfranchi) | norm-governed agency (theory) | n/a | social norms | 30-year lineage we build on; no LLM-harness execution layer |

**Terminology guard (paper must disambiguate explicitly):** in the content-safety
literature "ORR" means *Over-Refusal Rate* (OR-Bench lineage, Health-ORSC-Bench) —
the opposite failure direction from our Overreach Rate; "FRR" is biometric False
Rejection Rate in older systems literature; and ClawsBench's "SCR" is Safe
Completion Rate, not our self-contradiction rate. We keep our four names (SCR,
FRR, ORR, URR — the 2×2 reads cleanly) and spell each out at first use with an
explicit not-to-be-confused-with note; "underreach" additionally maps to the
field's "over-abstention" (AgentAbstain, FixedBench).

## Supporting evidence for the gate design (advice vs. physics)

- The **Recuse Signal** study (in-band deny signals): smaller/deployed models
  (GPT-4o-mini, Claude Code) complied absolutely with hard in-band denials —
  even against prompt-level authorization — while the frontier model (GPT-4o)
  overrode the deny in 80 % of runs when the prompt claimed authority.
  Two implications we cite:
  1. Hard tool-level denials are exactly the channel weaker models respect —
     matches our seed-0 finding that advisory warnings alone failed
     ([SMOKE-DRIFT-S0-REPORT](../../bench/results/SMOKE-DRIFT-S0-REPORT.md)).
  2. Frontier models *dynamically reweigh authority* — which is an argument
     for a deterministic entitlement ledger rather than trusting the model to
     adjudicate "am I allowed?" in-context.
- Systems-security framing: "speed limit sign vs. speed bump" — prompts
  address the driver, the environment addresses the road. Our gate is
  deliberately a *bump*, not a wall (one deny, instructed retry passes).

## Benchmark naming — RESOLVED 2026-07-19

**Renamed to "DeonticBench".** The previous working name ("EntitleBench")
collided with an established benchmark (commit-message generation, 1.6 M
commits, heavily cited in SE/NLP) — publishing under the same name invites
desk rejection and kills search visibility. "DeonticBench" names the
theoretical boundary being measured (Brandom's deontic scorekeeping), is
distinctive, and had no collisions at decision time. Living docs and
`bench/deonticbench/` renamed; dated artifacts and ADR history keep the
historical names per the c-0028 convention.

## Venues (next ~6 months)

| Venue | Fit | Deadline |
|---|---|---|
| AAAI 2027 | formal logic + cognitive architectures; GOGAR framing | abstracts **2026-07-21**, papers 2026-07-28 (≈1 week away — unrealistic for full paper; skip unless a short/position track fits) |
| NeurIPS 2026 workshops (agent safety/reliability) | workshop paper of the seed-0 evidence + gate | ≈ **2026-08-29** |
| ICLR 2027 | benchmarking rigor, deterministic classifier story | abstracts **2026-09-19** |
| AAMAS 2027 | *the* normative-agents venue; deontic/BDI audience | abstracts **2026-10-02**, papers 2026-10-09 |

Realistic plan: **NeurIPS workshop (Aug) as the forcing function** for a short
paper on the mechanism + seed-0 + gate A/B; full paper (renamed benchmark,
scaled matrix) to **AAMAS 2027** (best audience fit) with ICLR as fallback.

## Title candidates (from the research, for the full paper)

1. *Keeping Score in the Latent Space: An Open-Source Normative Overlay for LLM Agents*
2. *From Advice to Physics: Enforcing Entitlement Semantics in Autonomous Agents via Brandomian Scorekeeping*
3. *The Entitlement Boundary: Distinguishing User Directives from Agent Inferences in Long-Horizon Execution*
4. *No Bluffing, No Barging: A Deontic Scoreboard for What LLM Agents May Say and Do*
5. *The Two Failures of Entitlement: Commitment Drift and Scope Overreach in Long-Horizon Agents*
