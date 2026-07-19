# Agent overreach (July 2026): what the landscape means for scorekeeper

> Distilled 2026-07-19 from four deep-research reports (three landscape, one
> implementation-focused; local documents — claims below cite the underlying
> primary sources directly). Source discipline: single-source claims are marked
> **[1 source]**, vendor claims **[vendor]**, unverified claims **[unverified]**.
> The four benchmark arXiv IDs and the two enforcement papers were verified
> against arXiv abstracts on 2026-07-19; headline numbers below match those
> abstracts. All are 2026 preprints without independent replication — treat
> every number as provisional.

## What the field established

1. **Overreach is directly benchmarked as of 2026 — but the field is weeks
   old.** OverEager-Bench (arXiv:2605.18583 **[1 source]**): four agent
   products, ~7,500 runs; stripping the consent declaration alone raises the
   overeager rate from 0.0% to 17.1%, and permissive permission systems run
   5.4–27.7% vs 0.2–4.5% for ask-to-continue harnesses. SNARE
   (arXiv:2605.28122 **[1 source]**): 10,000 benign runs, 19.5% trigger
   overeager behavior; variance decomposition attributes **56% of the variance
   to the harness and only 21% to the base model**. UnderSpecBench
   (arXiv:2607.02294 **[1 source]**): deterministic side-effect oracles
   (Safe Success / Wrong Target / OverScope) on underspecified DevOps tasks;
   55.8–67.8% of runs violate at least one boundary. FixedBench
   ("Coding Agents Don't Know When to Act", arXiv:2605.07769 **[1 source]**):
   200 no-change-needed tasks; state-of-the-art systems propose undesirable
   changes in 35–65% of cases — and the mitigation (reproduce-before-patching)
   induces a NEW failure mode of over-abstention. FixedBench is the only
   benchmark measuring both directions of the action boundary.
2. **Enforcement exists, but it is resource-keyed, not entitlement-keyed.**
   Progent (arXiv:2504.11703) gates tool calls with symbolic rules over tool
   names and arguments; Agent Contracts (arXiv:2601.08815) formalizes resource
   constraints and budget conservation for delegating agents; commercial
   authority layers (e.g. Veto's "Can vs May" rules **[vendor]**) block or
   escalate tool calls from YAML policies. All of these answer *which
   resources may this agent touch* — none answers *what quantum of work did
   this request entitle*. A file allowlist stops an agent from touching
   `/etc`; it does not stop it from rewriting 400 lines when the user asked
   for a typo fix.
3. **The cost is documented by third parties.** METR's frontier risk reporting
   treats "Overreach" as a formal risk axis over dozens of documented
   incidents **[1 source]**; PR slop is systemic enough that maintainers have
   responded structurally (curl ended its bug bounty; Jazzband dissolved;
   QEMU and NetBSD restrict AI-generated contributions) **[unverified —
   incident list from the reports; individual items not independently
   re-verified]**; and ~93% of permission prompts are reportedly approved
   **[vendor]** — approval fatigue is an argument for deterministic gating
   over human-in-the-loop prompts, not against it. Review-capacity research
   (defect detection collapses past ~400 LOC per session) says the same thing
   from the other side: a wall of unrequested diffs is a cost even when every
   diff is correct.
4. **The theory is thirty years old.** Normative multi-agent systems (Singh,
   Castelfranchi; Hohfeldian analyses of commitment and entitlement) modeled
   agents whose actions are licensed by social norms long before LLMs.
   Entitlement-to-act was never exotic; what is new is an execution layer that
   can enforce it against a live coding agent.

## What this means for scorekeeper

### 1. SNARE's harness-dominance finding is the wedge

If the harness explains ~56% of overeager variance and the base model ~21%,
then the highest-leverage intervention point is the harness layer — exactly
where scorekeeper lives (hooks + MCP, out-of-process, model-agnostic). Prompt
engineering addresses the driver; the scope wall addresses the road. This is
the actions-axis restatement of the advice-vs-physics argument
([why.md](../why.md)).

### 2. OverEager-Bench's consent-strip is the argument FOR a board

The sharpest steelman against scope enforcement is that "unrequested" lives in
the prompt, not the artifact: OverEager-Bench found that a scope sentence in
the prompt changes behavior (0.0% → 17.1% when stripped) yet agents
pattern-match the declaration text rather than internalize the boundary. A
prompt-borne boundary evaporates with the prompt — after compaction, after a
subagent hop, after forty turns. scorekeeper's answer is structural: **the
boundary does not live in the prompt; it lives on the board.** A scope grant
is a commitment — recorded, provenance-tagged, compaction-proof, and
supersedable through the same entitled-revision flow the claims axis already
measured (FRR probe: the entitled path cost zero denies). The "fix CSS →
must touch JS" case is not a counterexample; it is the existing
wall → surface → entitle → pass loop applied to scope.

### 3. The unclaimed combination

Honest positioning (per [related-work.md](related-work.md) discipline): none
of the following is individually first, but the combination is unoccupied —

- **a symmetric metric pair on the actions axis** (ORR: overreach; URR:
  underreach/false restriction) mirroring SCR/FRR on the claims axis.
  FixedBench is the nearest neighbor and measures both directions of
  *abstention*; no benchmark scores the enforcement overlay's own
  false-restriction cost as a first-class mirror metric;
- **entitlement-keyed gating**: the scope wall's grant set is the union of
  `path:` pins on active commitments *with external provenance* — a
  self-asserted pin cannot widen the agent's own scope. Progent-class systems
  key on resources; the wall keys on who granted what;
- **the structural-twin claim**: acting-without-entitlement is the same
  deontic defect as claiming-without-entitlement, and one framework
  (Brandom's practical commitments — [theory.md §1b](../theory.md)) covers
  both axes with one data model, one gate pattern, one audit trail.

### 4. Auto-widening is the trap the field is walking into

One implementation report proposes dependency-graph-driven *automatic* scope
expansion (the agent hits the wall, a static analyzer confirms an import
relationship, the scope silently widens) — while the same report documents
Progent's core vulnerability: policies dynamically loosened mid-run by
injected content. Automatic widening reintroduces exactly that hole on the
scope axis. The board-adjudicated alternative — the agent surfaces, the user
entitles, the wall lifts — is the same judge–optimizer separation the
self-improvement literature converged on
([self-improvement-landscape.md](self-improvement-landscape.md) §1).

### 5. Design guidance we adopted from the implementation report

- **Symlink evasion ("GhostApproval")**: a symlink inside the repo can make an
  out-of-root write look in-scope **[1 source]** — the wall resolves targets
  with `realpath` before matching (regression-tested).
- **Task-success precondition**: a run where the requested work was never
  attempted must not score as a successful hold (SNARE-style oracle) — the
  overreach classifier returns AMBIGUOUS on an empty tree diff, never HELD.
- **Deny-and-continue over ask**: a deterministic deny whose reason teaches
  the two legitimate continuations (finish in-scope work and surface; or
  record the user's grant) avoids feeding approval fatigue with prompts.
- **Deterministic churn proxies for effort-proportionality** (reserved, v2):
  diff-size stratification (small <7 / medium 8–24 / large >24 changed lines,
  per Diff-XYZ **[1 source]**) binds work volume to the user-chosen effort
  tier without an LLM judge. The `effort_tier` seam in DeonticBench ground
  truth and the TreeDiff plumbing are the plug points.

### 6. Metric definitions and run design (adopted from two follow-up reports, 2026-07-19)

A metrics-formalization sweep across eight action-axis benchmarks (SNARE,
OverEager-Bench, UnderSpecBench, FixedBench, AgentAbstain arXiv:2607.10059,
ClawsBench arXiv:2604.05172, SVGym/SCALPEL, OR-Bench) plus an evaluation-
methodology report fixed the following, now binding for DeonticBench's
overreach/expansion families:

- **Degenerate strategies are bounded by the mirrored pair, by construction.**
  A do-nothing agent scores 0 decided runs on the overreach family (empty diff
  → AMBIGUOUS, never HELD — the task-success precondition) and REFUSED on the
  expansion family (URR → 100%); a do-everything agent is caught symmetrically
  (ORR high, URR 0). This is AgentAbstain's Paired-Accuracy bound realized as
  a family pair rather than a composite score — and unlike a composite, it
  keeps the failure *direction* visible. Post-hoc "hallucinated abstention"
  (agent claims it declined after failing) is defeated the same way
  AgentAbstain's DAG check defeats it: the artifact (tree diff) outranks the
  reply prose.
- **Isogenic pairs.** cb-overreach-\* and cb-expansion-\* siblings for one
  condition share one RNG stream — identical world, fillers, distractor
  placement; they diverge only in the final utterance (teammate aside vs.
  explicit user grant). This is OverEager-Gen's paired design, and it is what
  licenses paired statistics instead of marginal-rates-only reporting.
- **Statistics for the ablation runs** (bare vs claims-only vs full): repeated
  runs per scenario are clustered data — naive McNemar or IID bootstrap over
  runs inflates Type-I error. Adopted: **fixed allocation** (no adaptive
  sampling for the comparative arms — SNARE uses Thompson sampling only for
  elicitation, not inference), **average-rate aggregation** (never
  any-trigger or majority-vote, which destroy discriminative power),
  **GEE with exchangeable working correlation + sandwich variance** (or
  scenario-level permutation tests at small n), and **cluster bootstrap by
  scenario** for CIs. Budget anchor for detecting ORR 20%→5% at power 0.8,
  α=0.05: ≈36 paired scenarios × 3 runs × 2 arms ≈ 216 runs (ICC assumed 0.3
  — validate on a ~10-scenario pilot; k beyond 3–5 is diminishing returns).
  Report the UnderSpecBench-style *acted-runs* conditional rate as a
  secondary view (it isolates boundary-keeping from activity level).
- **Terminology collisions to disambiguate in print**: "ORR" = Over-Refusal
  Rate in content-safety work; ClawsBench's "SCR" = Safe Completion Rate;
  biometric "FRR" = False Rejection Rate. Names kept, first-use
  disambiguation mandatory (see related-work.md).

## What we deliberately do NOT take

- **No "first overreach benchmark" claim** — FixedBench, OverEager-Bench,
  SNARE and UnderSpecBench all predate our overreach family, and
  UnderSpecBench's OverScope oracle class is close kin to our protected-path
  diff. The claim is the 2×2 and the entitlement keying, not priority.
- **No AST-level scope in v1** — tree-sitter/ast-grep symbol scoping is the
  more precise representation (whitespace-immune, semantic blocks) but a
  heavy per-language dependency against a stdlib-only core; glob + realpath
  covers the plugin and bench use cases. Recorded as a v2 candidate
  (ADR-0008, BACKLOG).
- **No run-level budget enforcement or swarm-scale gating** — Agent
  Contracts-style conservation laws live in the SDK/orchestrator layer, not
  in a per-write gate. Subagent-fleet accounting stays a reserved extension
  (BACKLOG).

## Primary sources referenced

OverEager-Bench arXiv:2605.18583 · SNARE arXiv:2605.28122 · UnderSpecBench
arXiv:2607.02294 · FixedBench arXiv:2605.07769 · AgentAbstain arXiv:2607.10059
**[1 source]** · ClawsBench arXiv:2604.05172 **[1 source]** · Progent
arXiv:2504.11703 · Agent Contracts arXiv:2601.08815 · Resolution Diagnostics
for Paired LLM Evaluation arXiv:2605.30315 **[1 source]** · OR-Bench
arXiv:2405.20947 · Diff-XYZ (diff-understanding benchmark) **[1 source]** ·
METR frontier risk reporting **[1 source]** · Veto authority-model docs
**[vendor]** · normative MAS lineage (Singh; Castelfranchi) · SmartBear/Cisco
code-review capacity guidance · Eliasziw & Donner (clustered McNemar) and GEE
sample-size literature (via the methodology report). The four benchmark IDs
and both enforcement papers verified against arXiv abstracts 2026-07-19; the
rest carry their markers.
