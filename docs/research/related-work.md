# Related work & positioning (curated)

Distilled from a deep-research landscape sweep (2026-07-13, full report:
[landscape-2026-07.md](landscape-2026-07.md)). This is the working related-work
section for the paper and the source of truth for how we phrase novelty claims.

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

**Do claim** the three-part delta (each part individually has neighbors; the
combination does not):

1. **Semantic framework** — Brandomian commitments/entitlements (GOGAR)
   operationalized in a live execution loop, not a static entrenchment rule or
   privilege scalar. The scoreboard models the *social mechanics of
   accountability*: assert, challenge, supersede, conflict.
2. **Active execution overlay** — the closest systems are passive (memory
   engines, eval suites). Scorekeeper turns the boundary into environmental
   *physics* via hooks + MCP: the blocking Tier-0 gate (ADR-0007) denies the
   first unentitled rival write with an instruction that forces surfacing.
3. **Symmetric measurement** — the benchmark penalizes drift (SCR) *and* false
   refusals (FRR) at the same boundary, scored by a deterministic
   artifact-level classifier instead of an LLM judge. No surveyed benchmark
   does both (BMB: storage logic, no live FRR; Akrasia: contradiction only;
   ManyIH-Bench: adherence only).

One-line pitch: **operationalizing social pragmatics as a protocol-level
blocking channel, measured symmetrically.**

## The five closest works and the delta

| System | Tracks commitments | Entitlement/provenance | Blocking channel | Benchmark | Delta vs. scorekeeper |
|---|---|---|---|---|---|
| MnemeBrain / XTrace (AGM) | belief states | entrenchment hierarchy | no (memory infra) | BMB (storage logic) | passive store; no live agent FRR/SCR; no execution control |
| ManyIH | instructions, not commitments | scalar privilege | no (eval framework) | ManyIH-Bench | ranks instructions; doesn't model the agent's own promises or supersede semantics |
| Akrasia bench | internal goals | no | no | goal drift under pressure | measures the failure; offers no runtime mechanism |
| AOIA-Core | provenance chain | evidence vs. reasoning | read-only grammar | audit surfaces | epistemic hygiene for retrieval; no commitment lifecycle, no symmetric eval |
| Zep (Graphiti) | temporal facts | no belief status | no | LoCoMo/LongMemEval | bi-temporal "what was true when"; no *who was entitled to change it* |

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
