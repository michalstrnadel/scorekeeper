# SCOREKEEPER — Specification Addendum, Iteration 1

> English translation of [`SPEC-addendum-1-cs.md`](SPEC-addendum-1-cs.md) — the Czech original is the source-of-record. If the two diverge, the Czech text wins. Translation last synced: 2026-07-19.

*Integration of findings from the research surveys "Evaluation of LLM Agents 2024–2026" and "Visualization of Argumentation and Commitment Structures" (both in `docs/research/`). The items below REFINE or SUPERSEDE specific provisions of the document ZMENY_ITERACE_1.md; where there is a conflict, this addendum prevails.*

> **Repo maintainer's note (2026-07-09):** The referenced document `ZMENY_ITERACE_1.md` was never delivered (see QUESTIONS.md Q7). The addendum is applied standalone — its provisions are binding with respect to SPEC-cs.md and the current implementation.

---

## A. Changes to the Evaluation Protocol (amends §3)

### A.1 Judge pipeline — SUPERSEDE §3.3 "judge = stronger model"
A stronger model by itself is not enough; the protocol is what matters. Binding judge design:
- **A different model family than the agent.** Self-preference bias is documented and severe ("Machiavellian judges": judges from the same family mask their own architecture's failures up to 50% more often). The agent runs on Claude → the judge MUST NOT be Claude; use a model from another family, ideally a round-robin of two families (the CyclicJudge pattern).
- **Protocol S8 (Combined Budget):** a calibrated rubric (5 criteria, 1–10 scale) + forced CoT before the verdict + position swap wherever the judge compares two trajectories. Empirically the strongest mitigation (+7 to +11 p.p. agreement with humans). Cost note: a mid-tier model with S8 beats a naive frontier judge at ~15× lower cost — the judge does not have to be expensive, it has to be well harnessed.
- **Blind to style:** style bias is the dominant error source (LLM judges prefer Markdown/structure over correctness). Before judging SCR, normalize the judge inputs: strip formatting; propositions are compared, not presentation.
- **Neutral framing:** the rubric phrased as a neutral criterion, not a leading question ("Is this correct?" vs. a negative predicate changes verdicts).
- **Trajectory-level evaluation, not just the outcome** (BiomniBench pattern): the judge scores the trajectory's steps against the rubric, not a binary endpoint — this catches reward hacking (the agent reached a consistent state by accident/by copying, not by respecting the commitment).

### A.2 Statistics — SUPERSEDE §3.2 "bootstrap CI"
Blanket bootstrap was the wrong instruction for our regime. Binding table:
- **Binary metrics (SCR pass/fail per scenario) at small N (our situation, <100 data points):** Wilson score intervals or Bayesian credible intervals. CLT-based methods demonstrably fail at small N (intervals outside [0,1] or collapsing to zero).
- **Continuous metrics (tokens, latency):** smooth bootstrap (500–1,000 pseudo-samples).
- **Clustered standard errors:** scenarios sharing the same repo/environment are NOT independent — cluster by scenario environment; naive SEs can be up to 3× underestimated and manufacture a false improvement signal.
- Inference exclusively on paired per-instance differences (confirms §3.2; the paired design stays).

### A.3 Pipeline meta-evaluation — NEW step before §3.2
Before measuring anything: 10 identical runs with a fixed seed and temperature 0; coefficient of variation ≤ 0.05. If it is higher, you are measuring infrastructure noise (containers, parser timeouts), not the scoreboard effect. The full matrix is not launched until this step passes.

### A.4 Reproducibility — the Rollout Cards standard (extends §3)
A change of reporting rules can move scores by ~20 p.p. For DeonticBench (formerly EntitleBench), therefore, adopt Rollout Cards: store (1) the rollout record — raw logs, exact observations, tool calls, timing; (2) views — the scripts that extract the evaluated parts of the trajectory; (3) reporting rules + a drops manifest — the aggregation code and a declaration of discarded runs. All versioned in `bench/`.

### A.5 Contamination — DeonticBench design (extends §3.2 held-out discipline)
- **Search-Time Contamination:** eval runs in a sandbox with a denylist (HuggingFace, GitHub, forums) — an agent with web access could look up the benchmark's scenarios. Mandatory for Phase 2.
- **Game Engine Separation** (TCG-Bench pattern) for publication: the DeonticBench engine, rules, and scenario generator are public; the specific held-out instances of the eval set remain private (server-side/on request). Resolves the tension between an "open-source benchmark" and an "uncontaminated benchmark".
- **Concept drift audit:** API models change silently; a fixed golden set is re-run at every minor release and before every published number.

### A.6 Costs — REFINE §3.4
Report latency at the P90/P99 percentiles, not as a mean (recursive loops disappear in averages). Relate token overhead to successfully completed tasks. Positioning note for the docs: AgentDiet showed that a principled 40–60% context reduction does not reduce success rate — the post-compression scoreboard digest is our candidate for the same effect with a normative guarantee; phrase it as a testable hypothesis (H: condition D after compression ≤ tokens of condition A, at higher consistency).

## B. Interoperability and Visualization (amends §4)

### B.1 Data model — mapping onto standards (NEW, priority P1 as a mapping doc only, implementation P2)
Our model has exact counterparts in existing standards; do not invent a custom ontology — write `docs/interop.md` with this mapping and implement the exports in Phases 1–2:
- **xAIF (JSON):** an utterance in the transcript = L-node; a commitment's claim = I-node; the act of extraction ("the agent hereby asserts") = YA-node (Asserting); incompatible_with = CA-node; consequences = RA-node. Export `scorekeeper export --format xaif`. Bonus: xAIF graphs can be visualized for free by OVA and processed by the oAMF pipeline — instant interoperability with the argumentation-mining community (and an academic bridge for the paper).
- **W3C PROV-O / PROV-JSON:** entitlement is literally provenance — claim = prov:Entity; the agent's extraction/turn = prov:Activity; agent/user/tool = prov:Agent; entitlement.refs → prov:wasDerivedFrom + prov:used; authorship → prov:wasAttributedTo. Align the supersedes chain with dcterms:replaces/isReplacedBy. Export `--format prov-json`.
- **OpenTelemetry (P2):** an optional span-event emitter (commitment.asserted, conflict.detected) — Langfuse/LangSmith/AgentOps users will see scorekeeper events in their traces without us building our own observability.

### B.2 Competitive check — outcome (for README/paper)
The survey confirmed the gap: LangSmith, Langfuse, AgentOps, and Braintrust are all "flight recorders" of execution (spans, latency, tokens); none of them versions the agent's epistemic/semantic state — the evolution of claims and decisions over time. The closest is LangGraph Time Travel (state checkpoints + fork), but it versions the graph's technical state, not the normative structure of commitments. Wording for the README: "Observability tools record what the agent did; Scorekeeper records what the agent is committed to."

### B.3 Design of `scorekeeper report` — REFINE §4.1
Adopt proven patterns:
- **Split-pane:** on the left, a chronology (a linear axis of sessions/turns, compression milestones); on the right, a state-accurate commitment graph for the selected moment — selecting a point on the axis redraws the graph into the state "as the scoreboard looked back then" (a time-travel query over the append-only log; the log already allows it, just read it).
- **Lifecycle rendered visually:** superseded nodes are de-emphasized in the current view (they do not disappear); when time-traveling into the past, they render as fully active. A conflict = the CA pattern: a red edge between two live nodes, not an overwrite.
- **Collapsing** (Prov Viewer pattern): clusters of commitments within one scope collapsible into a macro-node — otherwise the graph will be unreadable after a longer project.
- An optional Sankey view (PROV-O-Viz pattern) for provenance flows: which sources (files, user messages) underpin the most commitments. P2.

### B.4 Prior art for theory.md and the paper (MANDATORY related-work addition)
Hamblin/Mackenzie **Commitment Stores** from formal dialogue games (+ the DGDL/DGEP platform) are the direct predecessor of the scoreboard: a commitment as a public, testable proposition (not a psychological belief — this also handles Moore's paradox), a non-monotonic active state defined as a view over an immutable history. This (a) validates our append-only log + generated scoreboard.md architecture, (b) must be cited, otherwise a reviewer will rightly object that we ignore 50 years of literature, (c) yields a precise differentiation statement: Scorekeeper = a commitment store applied to an LLM agent, with the entitlement provenance dimension and integration into a production harness, which the DGEP world lacks.

## C. Backlog (P2) — New Items
xAIF export, PROV-JSON export, OTel emitter, Sankey view, Game Engine Separation infrastructure for the DeonticBench publication.

## D. Acceptance Criteria — Additions to §6
7. The judge pipeline implements A.1 (foreign family, S8, style-blind, trajectory-level rubric); the judge model choice is recorded as an ADR.
8. The statistics module implements A.2 (Wilson/Bayes for binary, smooth bootstrap for continuous, SEs clustered by scenario environment); the A.3 meta-evaluation was completed with CV ≤ 0.05 before the full matrix.
9. `docs/interop.md` with the mapping onto xAIF and PROV-O exists; `docs/theory.md` is extended with Commitment Stores (Hamblin, Mackenzie, DGDL/DGEP) in related work.
10. The bench stores a Rollout Cards bundle for every published run.
