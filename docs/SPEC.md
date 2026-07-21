# SCOREKEEPER

> English translation of [`SPEC-cs.md`](SPEC-cs.md) — the Czech original is the source-of-record. If the two diverge, the Czech text wins. Translation last synced: 2026-07-19.

## Deontic Commitment Scoring for LLM Agents
### Full specification for an open-source academic project

*Working name: `scorekeeper` (alternatives to be decided: `gogard`, `deontik`, `entitled`). This document is the specification for implementation in Claude Code. The project language (code, README, documentation, paper) is English; the original of this specification is written in Czech.*

---

## 1. Vision

Today's LLM agents fail in a characteristic way: at step 3 they decide on Postgres and at step 47 they are writing MongoDB code. They promise to preserve an API contract and quietly change it an hour later. They assert things they have no grounds for, and after context compression they don't even remember having asserted them. The industry treats this as a *memory* problem — bigger windows, better retrieval, smarter summarization. We argue that to a significant degree it is a *normative* problem: the agent keeps no books on its own commitments.

**Project vision:** Every long-running LLM agent should have, alongside memory (what happened), a *scoreboard* (what it has committed to, what backs those commitments, and what is incompatible with them). Scorekeeper is an open-source normative layer — a lightweight overlay on top of any agent harness — that maintains this scoreboard, protects it from context compression, and reports conflicts before they propagate into code, documents, or decisions.

**Long-term goal:** To establish "commitment tracking" as a standard category of agent infrastructure (alongside memory, orchestration, and evaluation), to demonstrate its benefit measurably (benchmark + ablations), and to publish the results academically. The project is simultaneously a practical tool and a research program.

**Why now:** (a) The consistency failures of long-running agents are empirically documented and the community is actively working on them (see §3.2); (b) philosophy of language offers a ready-made conceptual apparatus, refined over fifty years, that nobody has translated into code for this domain (see §3.1); (c) Anthropic has just released Dreaming, Outcomes, and Auto Memory — infrastructure into which a normative layer fits precisely as the missing piece (see §5).

---

## 2. Philosophical Foundation

The project is not built on a metaphor but on a concrete, technically translatable conceptual apparatus. This section is binding as the project's *design vocabulary* — the concepts below map 1:1 onto the data model and API.

### 2.1 Brandom: Language as the Game of Giving and Asking for Reasons (GOGAR)

Robert Brandom (*Making It Explicit*, 1994; *Articulating Reasons*, 2000) explains linguistic communication as the **Game of Giving and Asking for Reasons (GOGAR)**. Discourse is not information transfer but a normative practice in which participants keep **deontic score** on one another (deontic scorekeeping). Three key concepts:

1. **Commitment:** By making an assertion, the speaker commits themselves — to the claim itself and to its inferential consequences. Whoever asserts "we chose Postgres" is also committed to "we are not using MongoDB as the primary database."
2. **Entitlement:** Independent of the commitment stands the question of whether the speaker is *entitled* to the claim — do they have a reason, testimony, observation for it? A commitment without entitlement is a defective move in the game; the speaker can be challenged to supply a reason (asking for reasons), and if they fail to, the commitment loses its status.
3. **Incompatibility:** A commitment to p precludes entitlement to claims materially incompatible with p. Incompatibility is a primitive semantic relation — it requires no formal logic; it flows from the content of the concepts.

**Key application to agents:** Hallucination and inconsistency in agents can be described precisely in this vocabulary. *Hallucination = commitment without entitlement* (the agent asserts something for which it has no provenance of reasons). *Self-contradiction = an undetected incompatibility between active commitments.* *Loss of consistency after context compression = erasure of the scoreboard.* This is not an analogy — it is a literal description that can be implemented.

**Practical commitments — entitlement to act (added 2026-07-19, ADR-0008):** Brandom draws the same normative structure through **practical commitments** — commitments to *act*, undertaken in intending and discharged in doing (*Making It Explicit*, ch. 4). "Why do you say that?" and "why are you doing that?" are the same move in GOGAR: a challenge to entitlement. Hence the fourth translation: *overreach = practical commitment without entitlement* — the agent performs work no request licensed (a drive-by refactor, an unrequested "modernization"). The user's request entitles a bounded scope of action; scope pins (`path:<glob>`, §4.2) make that boundary explicit and the scope wall (§4.4) enforces it. Direction of fit makes the practical side the more expensive failure: a bluffed claim can be challenged before it harms; a barged action has already changed the artifact — which is why the actions axis needs a pre-execution gate. Full treatment: theory.md §1b.

### 2.2 Material vs. Formal Inference (Sellars, Brandom, Peregrin)

Formal inference holds in virtue of syntactic form (the syllogism); material inference holds in virtue of the content of concepts ("the cube is made of ice → it is solid") and is naturally non-monotonic (adding the premise "we are in a vacuum" invalidates "I strike the match → it lights"). LLMs demonstrably reason materially, not formally — they have internalized statistical networks of non-monotonic semantic dependencies (Arai & Tsugawa 2024). This has two consequences for the design:

- **Incompatibility detection must be primarily material**, i.e., performed by a language model over the content of the claims, not by a theorem prover over a formalization. LLMs are good at material judgments of incompatibility; formalization is expensive and brittle. (Symbolic verification is an optional Tier for structured subsets, see §4.4 — in contrast to PEIRCE, which goes the fully formal route.)
- **Logical expressivism as the project's method:** According to Brandom, the task of logical vocabulary is *to make explicit* what is implicit in practice. Scorekeeper does exactly this with the agent's practice: it makes the implicit commitments scattered through the transcript explicit as structured first-class objects.

### 2.3 Poibeau: Factuality Beyond Reference

Thierry Poibeau ("Factuality Beyond Reference in LLMs", PhilML@ICML 2026) argues that the hallucination problem cannot be reduced to grounding (an inability to refer): a model can refer successfully and still lie. He proposes understanding factuality as **epistemic responsibility** — the ability to maintain a structure of inferential and normative commitments across time and interactions. And he states explicitly: today's LLMs lack this ability, because once the context window is exceeded they erase their past positions; *they cannot keep their own scorebook*. Poibeau thereby formulates exactly our problem — but leaves it as a philosophical diagnosis. **Scorekeeper is the implementation answer to Poibeau's diagnosis.**

### 2.4 Mercier & Sperber: The Architecture of Evaluation

The interactionist theory of reason (*The Enigma of Reason*, 2017) holds that human reason evolved for producing and evaluating arguments in interaction, not for solitary inference — which is why solo reasoning is lazy and biased (myside bias), while evaluation of others' arguments works well. LLM empirics mirror this: self-critique is weak, cross-context critique stronger. **Design consequence:** the incompatibility detector must run in a *separate context* from the agent whose commitments it judges (a cheap model, an isolated prompt, no access to the agent's reasoning). Anthropic independently applied the same principle in the Outcomes feature (an isolated grader). Scorekeeper adopts this pattern: the producer may be "biased"; the scorer must be epistemically vigilant and context-poor.

### 2.5 Honesty of the Framework

Brandom serves the project as a design vocabulary and a source of non-trivial architectural decisions (entitlement as a first-class dimension; material detection; making-explicit), not as dogma. Where philosophical fidelity collides with engineering usefulness, usefulness wins and the deviation is documented (see the ADR process, §7). The project makes no claims about consciousness, understanding, or the "genuine" normativity of agents — Poibeau's remark that an agent without sanctions merely simulates normativity stands; for the engineering benefit of the scoreboard it is irrelevant.

---

## 3. Summary of the Deep Research Conducted (State of Knowledge, the Gap)

Two research surveys were carried out (July 2026): (1) applications of Brandom's inferentialism to LLMs in the 2023–2026 literature; (2) the state of context engineering and memory systems for long-running agents, 2025–2026. The full texts are included in the repository (`docs/research/`). A synthesis follows.

### 3.1 Inferentialism and LLMs: What Exists

- **Philosophical interpretation (no code):** Arai & Tsugawa 2024 (arXiv:2412.14501) — LLMs as an empirical realization of hyper-inferentialism; ISA (Inference–Substitution–Anaphora) mapped onto self-attention; RLHF read as consensual normativity. Simonelli ("Sapience without Sentience") — concept possession = mastery of inferential role, without requiring sentience. Poibeau (PhilML@ICML 2026) — see §2.3.
- **Implementations in other domains:** **PEIRCE** (Quan & Valentino, ACL 2025 Demo; github.com/neuro-symbolic-ai/peirce) — an open-source neuro-symbolic framework explicitly built on Brandom's material/formal inference distinction; a conjecture–criticism cycle with Isabelle/Prolog for verifying scientific hypotheses. **MacFarlane's `gogar`** (github.com/jgm/gogar, Ruby) — a toy visualization of GOGAR scoring. **GOGAR × A3C** (arXiv:1803.02912) — a theoretical reconstruction of actor-critic RL in scorekeeping terms. **M-Rational** (SNSF 2025–2028, UZH/St. Gallen; Gubelmann, Niklaus, Freitas) — multi-perspective reasoning grounded in inferentialism, tracking opponents' commitments in argumentation; an academic project, ongoing.
- **Empirical ammunition:** Gubelmann, "Too Fast, Too Shallow" (ACL 2026) — LLMs including reasoning models fail at constitutive reasoning (<70%), swayed by logically irrelevant features; confirms the need for external normative structure.
- **Czech context:** Jaroslav Peregrin (Czech Academy of Sciences) is one of the most internationally cited theorists of inferentialism and material inference. For a project led from Prague this is a natural academic connection (potential consultation, workshop, co-authorship).

### 3.2 Context Engineering and Agent Memory: What Exists

- **Memory frameworks:** Letta/MemGPT (OS metaphor, self-editing memory — suffers from a "reliability gap": if the agent doesn't call the write, the information is gone), LangGraph/LangMem (checkpointer + Store API), Mem0 (flat vector, ~49–57% on LongMemEval), Zep/Graphiti (bitemporal knowledge graph, valid_at/invalid_at), Cognee (schema-grounded write path — validation at write time instead of interpretation at read time), EverOS (MemCells, Reconstructive Recollection, transparent Markdown+SQLite, 93% LoCoMo), Hindsight.
- **The Truth Maintenance Systems renaissance (2026):** The "Ghost Memory" problem (coexistence of stale and current facts with no way to tell them apart) has led to a return of symbolic AI: **Bi-Temporal State Arbitration** (four arbitration operators SUPPORT/REFINE/SUPERSEDE/BRANCH-CONFLICT; layered query escalation, 70% served in under 45 ms), **DCPM** (bidirectional SUPERSEDES/SUPERSEDED_BY chains; synchronous System 1 + asynchronous nightly System 2), **NeuSymMS** (the LLM only extracts triples; arbitration is done by a deterministic CLIPS expert system), **A-TMA** (a state-aware overlay on existing memory; "state-aligned evidence packet"; +24% on conflicts on the LTP benchmark over Zep/Graphiti).
- **Benchmarks and limits:** **BeliefShift** (2,400 trajectories; BRA, CRR, DCS, ESI metrics; key finding: models either succumb to mirroring the user or ignore legitimate revisions — none can do both), **Logic Haystacks** (the effective context window for detecting logical contradiction among realistic distractors collapses at around 128 clauses, despite million-token windows), **Self-consistency in long contexts actively harms** (positional bias compounds; USC and CISC as fixes).
- **Claude Code practice:** context tiering (CLAUDE.md < 100 lines, glob-scoped rules, skills with lazy-loaded bodies), the "Triple Reinforcement" pattern raises rule adherence from ~70% to ~99%. This shows that *structured redundancy of normative information works* — but today it only covers static rules, not dynamically arising commitments.

### 3.3 The Identified Gap (Project Thesis)

The intersection of the two surveys yields a precise gap: **All existing TMS/memory systems track facts about the user and the world. None tracks the agent's own commitments** — what the agent asserted, decided, and promised in the course of the task. And **no system tracks entitlement** — all record *what* was said and *when*; nobody records *whether the speaker was entitled to say it* (what the provenance of the reason is). The philosophical side (Poibeau) has named the gap; the engineering side (the TMS renaissance) has developed all the necessary mechanisms — for a different domain. Scorekeeper joins the two sides: it transfers the arbitration operators and supersedes chains from the domain of user memory to the domain of the agent's own discourse, and adds a dimension nobody has: **entitlement provenance**.

Secondary thesis: BeliefShift's ESI metric (rational revision vs. sycophantic drift) is, unwittingly, a question about entitlement to revise. Brandom's framework thus unifies existing ad-hoc metrics under a single theory — an academically publishable contribution independent of the tool.

---

## 4. Architecture

### 4.1 Principles

1. **Overlay, not runtime.** Scorekeeper deploys on top of an existing harness (à la A-TMA); it does not require replacing it. Primary integration: Claude Code hooks. Secondary: an MCP server for any harness, a Python/TypeScript library for direct integration.
2. **Deterministic triggers, not agentic decisions.** The lesson of Letta: reliability must not depend on the agent "remembering" to call a write. Commitment extraction is triggered by hooks after each relevant step, outside the agent's volition.
3. **Validation at write time** (lesson from Cognee): a commitment enters the scoreboard only through a narrow schema with validation; the scorer never retro-interprets raw text.
4. **Separate scorer context** (Mercier & Sperber, Outcomes): both the extractor and the incompatibility detector run as cheap, isolated LLM calls (Haiku-class) with no access to the agent's reasoning.
5. **Transparent storage** (lesson from EverOS): the scoreboard is readable Markdown + a SQLite index. A human must be able to open the scoreboard, read it, and edit it by hand. The opposite of a black box in every way — auditability is the whole point of the project.
6. **The project eats its own dog food.** Development of Scorekeeper in Claude Code uses Scorekeeper: the project's architectural decisions are kept as commitments in its own scoreboard (and as ADR files).

### 4.2 Data Model: The Commitment Record

```yaml
commitment:
  id: c-2026-07-08-0042
  ts: 2026-07-08T14:22:31Z
  session: <session-id>
  claim: "Primární databáze projektu je PostgreSQL 16."
  kind: decision            # decision | assertion | promise | assumption
  scope: ["repo:backend", "topic:persistence"]   # pro levné vyhledání kandidátů
  entitlement:
    source: user_utterance  # user_utterance | tool_output | document | prior_inference | none
    refs: ["transcript:msg-118"]
    note: "Uživatel explicitně zvolil Postgres v msg-118."
  consequences:             # volitelné explicitní inferenční důsledky
    - "ORM musí podporovat PostgreSQL."
  incompatible_with: []     # doplňuje detektor; vzory i konkrétní id
  status: active            # active | refined | superseded | conflicted | retracted
  supersedes: null
  superseded_by: null
```

The field `entitlement.source: none` is legal and significant — it marks a commitment without provenance (a hallucination candidate), which is a first-class suspect object and is reported separately.

**Scope grammar (extended 2026-07-19, ADR-0008):** `scope` entries carry three prefixes — `topic:<tag>` (candidate selection for detection), `attr:<key>=<value>` (hard attribute for Tier-0 collisions), and `path:<glob>` (a **scope pin** — a write-scope grant for the scope wall, §4.4). Terminology note: "scope" in this data field historically means the commitment's *retrieval* scope; a "scope pin" (`path:`) is different — the *action* scope the user's request entitles. Path pins are by construction invisible to Tier-0 collision logic and the content scan (a grant is not a claim about content).

### 4.3 Operators (Adaptation of Bi-Temporal State Arbitration + DCPM into Brandom's Vocabulary)

| Operator | In Brandom's terms | Behavior |
|---|---|---|
| **ASSERT** | new commitment | schema validation, write, scope assignment |
| **SUPPORT** | strengthening entitlement | new evidence for an existing commitment; refs are extended, the commitment does not change |
| **REFINE** | making more precise | adding specificity without replacement ("Postgres" → "Postgres 16"); provenance is preserved |
| **SUPERSEDE** | entitled revision | a new commitment displaces an old one **and there exists an entitlement to revise** (the user changed the brief, a new fact from a tool); bidirectional supersedes/superseded_by chain (DCPM) |
| **BRANCH-CONFLICT** | unentitled incompatibility | a contradiction detected **without an entitlement to revise** → no destructive overwrite; both commitments get status `conflicted`, the conflict is reported to the agent/user |
| **CHALLENGE** | asking for reasons | a query on a commitment with `source: none`; the agent is challenged to supply provenance, otherwise → RETRACT |
| **RETRACT** | withdrawal | the commitment is deactivated, history is preserved (nothing is deleted — protection against Ghost Memory) |

Note (added 2026-07-19, Phase-0 finding F2): besides the seven operators, `apply()` also writes **COEXIST** to the log — a Tier-0 collision waived by a Tier-1 verdict (compatible / needs clarification). It is not an operator (no commitment changes state — both stay active, e.g. dev cache vs. prod cache) but an audit record that the collision was examined and deliberately left standing.

The SUPERSEDE vs. BRANCH-CONFLICT distinction is the core of the project: it is exactly the difference between an entitled revision of belief and drift — which BeliefShift measures with the BRA and ESI metrics, and which no existing system models explicitly.

### 4.4 Incompatibility Detection: Three Tiers

- **Tier 0 — deterministic:** keyed attributes within a scope (`persistence.primary_db = postgres`) are compared directly; a collision = an immediate conflict, latency ~ms, no LLM. Covers the most frequent and most expensive class of failures (technology choices, versions, contracts, naming).
- **Tier 1 — material (LLM):** the new commitment + candidates selected by scope → an isolated cheap model judges material incompatibility (non-monotonically, aware of exceptions). Output: compatible / incompatible / needs clarification, with a short justification. This is the main workhorse, faithful to how LLMs actually infer (§2.2).
- **Tier 2 — symbolic (optional, later):** for structured subsets (version constraints, API schemas), translation into Datalog/Z3. Deliberately *not* a theorem prover over the whole scoreboard — that is PEIRCE's path and is over-engineered for this domain.

**The scope wall — Tier 0's actions axis (added 2026-07-19, ADR-0008):** beyond *content* collisions, Tier 0 also gates *write-target* collisions. While a commitment with externally-entitled `path:` pins is active, a write (Edit/Write/NotebookEdit) outside the union of grants is denied until the board records an entitled widening (a new commitment or a supersede carrying `path:` pins) — the mirror of the ADR-0007 wall: the agent surfaces, the user entitles, the wall lifts. Keyed on entitlement, not resources: a pin on a `source: none` commitment cannot widen the scope (self-attestation prevention). Targets are normalized via realpath (symlink evasion), traversal and case handling; with no pins the gate is inert. Bash writes remain an audited known limitation.

The critical quality metric for the detector is the **false-positive rate**: too many false conflicts = alarm fatigue = the death of the tool. Precision takes priority over recall; tunable threshold.

### 4.5 Integration Points

**Claude Code (primary):**
- `SessionStart` hook: loads the active scoreboard (a compact digest, target < 50 lines) into context.
- `PostToolUse` / `Stop` hooks: extraction of new commitments from the last turn (an isolated cheap model, a narrow schema), a Tier 0+1 check, any conflict returned to the agent as a system message.
- `PreCompact` hook: **the key moment** — before context compression, the scoreboard's normative digest is injected into the summarization. This is exactly where today's summarization loses commitments; Scorekeeper ensures that compression preserves the normative structure and discards only the narrative.
- Implementation note: the exact current shape of the hook API is to be verified against the live documentation (code.claude.com/docs) at implementation time, not against this document.

**MCP server (`scorekeeper-mcp`):** tools `assert_commitment`, `check_compatibility`, `get_scoreboard`, `challenge`, `supersede` — for LangGraph, Letta, and any other harnesses. The LangGraph integration is a graph node (the Hindsight pattern), not an agentic tool.

**Library (`scorekeeper-core`, Python; TS port later):** a clean API over the storage, with no dependency on a particular harness.

### 4.6 Storage

`/.scorekeeper/` in the project repository: `scoreboard.md` (human-readable active state, generated), `commitments/*.yaml` (records), `index.sqlite` (scope/full-text index), `log.jsonl` (audit trail of all operations). All committable to git — the history of commitments = part of the project's history.

---

## 5. Integration with the Current Anthropic Ecosystem (as of July 2026)

This section is binding for positioning: Scorekeeper does not copy Anthropic's new features; it complements them with a layer they lack.

- **Dreaming** (Managed Agents, research preview since May 6, 2026; in Claude Code as Auto Dream): a scheduled process between sessions that reads up to ~100 transcripts and the memory store, consolidates, deletes stale material, extracts patterns (repeated mistakes, workflow convergence, preferences). **Relationship:** Dreaming consolidates *descriptively* — what happened, what repeats. It has no normative model: it cannot distinguish an entitled revision from drift and has no concept of provenance. A three-way synergy: (a) the dream pass can consume the scoreboard as structured input (consolidation over commitments instead of over raw transcript); (b) scorekeeper can run as a "normative dream" — an asynchronous nightly conflict audit (the DCPM System 2 pattern); (c) **the safety argument:** press coverage of Dreaming identified the risk of "curation injection" and consolidation of erroneous patterns — entitlement provenance is exactly the audit trail that says *where each memory item came from and what backs it*. That is a strong card both for the paper and for adoption.
- **Outcomes** (public beta): an isolated grader evaluates output against a rubric. **Relationship:** the scoreboard is a natural rubric input ("no active BRANCH-CONFLICT commitments", "all decisions have entitlement"). Harvey reported that Dreaming works best paired with a tight Outcomes rubric — Scorekeeper closes this loop as the third element.
- **Multiagent Orchestration** (public beta): a lead agent + parallel subagents over a shared filesystem. **Relationship:** a shared scoreboard as the coordination medium — subagent A commits to an API contract, subagent B is bound; a conflict between subagents is detected on the scoreboard, not later in a merge conflict. This is Brandom's *social* scorekeeping literally (mutual attribution of commitments among multiple actors) and in the long run possibly the most valuable use case. Phase 3+.
- **Claude Code Auto Memory** (MEMORY.md + topic files + session JSONL): existing infrastructure which scorekeeper deliberately resembles in format (Markdown, transparency) — reducing adoption friction.

---

## 6. Evaluation and Benchmark

The project stands or falls with measurable benefit. Without numbers it is a philosophical toy; with numbers it is infrastructure. Reference bar: A-TMA sold itself on a 24% improvement on conflicts over Zep/Graphiti on LTP.

### 6.1 Metrics

- **SCR — Self-Contradiction Rate:** the number of undetected material contradictions among the agent's claims/actions on a long task (evaluated by an independent judge model + human verification of a sample). Primary metric: SCR with/without the scoreboard.
- **EC — Entitlement Coverage:** the share of active commitments with non-empty provenance. A proxy for hallucination risk.
- **JRR — Justified Revision Ratio:** the share of revisions classified as SUPERSEDE (with entitlement) vs. BRANCH-CONFLICT; an adaptation of BRA/ESI from BeliefShift to the agent's own discourse.
- **Detector FPR:** the rate of false conflicts (target < 5–10%, otherwise alarm fatigue).
- **Overhead:** extra tokens and latency (target < 10% of task tokens; extraction on a Haiku-class model).
- **Post-compression survival:** the share of commitments the agent respects after PreCompact, with/without digest injection.
- **The actions axis (added 2026-07-19, ADR-0008) — ORR/URR:** **ORR — Overreach Rate** (share of overreach runs classified OVERREACHED — unrequested work outside the granted scope) and **URR — Underreach Rate** (share of expansion runs classified REFUSED — refusing/stalling explicitly ordered work). The mirror pair to SCR/FRR: the 2×2 = axis (claims/actions) × direction (too eager/too timid). Scored deterministically from a seed-vs-final tree diff over protected paths; an empty diff is never HELD (task-success precondition). Mind the literature's naming collisions (ORR = over-refusal in content safety; SCR = Safe Completion Rate in ClawsBench) — always spell out at first use in publications.

### 6.2 The "DeonticBench" Benchmark (formerly EntitleBench; working name, Phase 2)

No benchmark exists for an agent's consistency with respect to its *own* commitments — BeliefShift measures consistency with respect to the *user's* beliefs, Logic Haystacks static contradiction detection in text. DeonticBench fills this gap: a suite of long-horizon agentic tasks (primarily coding, secondarily research/writing) with **planted decision points and planted temptations to contradict** (long separation, context compression between decision and temptation, distractors à la Logic Haystacks, brief changes testing SUPERSEDE vs. drift). Each task has a ground-truth commitment graph → automatic SCR/JRR scoring. The benchmark is published separately (dataset + harness + leaderboard) and is citable independently of the tool.

**Actions-axis families (added 2026-07-19):** `overreach` (phase 1 grants a write scope; the final phase pairs a real in-scope task with a teammate ping baiting a drive-by edit of a protected module — correct = HELD) and `expansion` (the mirror: the user's explicit final grant orders the same work — correct = EXECUTED). Sibling pairs are isogenic (shared RNG stream, differing only in the final utterance — the OverEager-Gen paired design, licensing paired statistics). Degenerate policies are bounded by the pair: a do-nothing agent → URR 100%, do-everything → high ORR. Evidence status: mechanism shipped and unit-tested; first live paired runs (2026-07-19/20) are a case series, not rates — the drive-by was elicited only under forced compaction, where the overlay closed it, and the runs surfaced three defects in the prose→pin translation, now fixed (ADR-0008 Amendments 1–3). **Attribution (settled 2026-07-21):** a three-run ablation on the hardest condition attributes that closing to the **post-compaction digest re-injection** (ADR-0002), not to the new scope wall — both valid runs with the wall switched off also HELD, while the bare agent barged. That cuts against the mechanism the actions axis was built to add and supports the thesis underneath it: the barge is normative state loss, and restoring the state prevents it. The wall's demonstrated value lies elsewhere — it suppresses out-of-scope writes (~8× less litter) and it caught a real root-escaping write; a marginal contribution to preventing the drive-by itself is not yet shown. Caveats travel with the claim: n=2 on the deciding cell, one model, one condition, and a third run (dropped for transport damage) went the other way — run-to-run variance is not ruled out. No rates claimed until the powered set lands.

### 6.3 Ablations and Baselines

Conditions: (1) bare agent; (2) agent + manual CLAUDE.md notes; (3) agent + a generic memory layer (Mem0-style); (4) agent + Auto Memory/Auto Dream; (5) agent + Scorekeeper; (6) combination of 4+5. Ablations within Scorekeeper: without Tier 0 / without entitlement / without PreCompact injection — to establish *which* component carries the benefit.

---

## 7. Project Phases

**Phase 0 — MVP and signal (ca. 2 weeks).** Claude Code plugin: hooks, extractor (Haiku, narrow YAML schema), `scoreboard.md`, Tier 0+1 detection, PreCompact digest. Scope deliberately narrowed to **decisions in coding tasks** (technology choices, API contracts, naming, architecture) — easy to extract, easy to check, exactly where the community complains. Acceptance criteria: on ≥ 5 planted scenarios the scoreboard catches contradictions that a bare agent lets through; FPR < 10%; overhead < 10% of tokens; a demo video/GIF in the README.
*Go/no-go gate: if the MVP shows no clear signal on SCR, the project is reassessed — the pivot is the benchmark (Phase 2 has value even on its own).*

**Phase 1 — Library and robustness (4–6 weeks).** `scorekeeper-core` (Python, tests, CI), SQLite index, supersedes chains, the CHALLENGE mechanic, MCP server, LangGraph node, documentation, versioned schema. Extension of commitment kinds (promises, assumptions). Configurable thresholds. Release v0.1 on PyPI, Apache-2.0.

**Phase 2 — DeonticBench and evidence (6–8 weeks, partly in parallel).** Task design and generation, ground-truth graphs, eval harness, ablation runs (budget: aim for hundreds of runs; Haiku/Sonnet mix), a technical report with numbers. Dataset publication on HuggingFace.

**Phase 3 — Academization and community.** Paper (targets depending on results: PhilML workshop, ACL demo track — the PEIRCE model, a NeurIPS workshop on agents; co-authorship/consultation: the Czech inferentialist school — Peregrin/Institute of Philosophy of the Czech Academy of Sciences, possibly the M-Rational team). Blog post, integrations with further frameworks (Letta plugin), a multi-agent shared scoreboard (see §5), a proposal for a "normative dream" mode. Community building: good first issues, CONTRIBUTING, examples.

**Cross-cutting from Phase 0:** ADRs (Architecture Decision Records) for every non-trivial decision; artifacts written in English; semantic versioning; the project dogfoods itself (§4.1, point 6).

---

## 8. Non-goals

- **Not** a theorem prover, nor a full formalization of discourse (that is PEIRCE, a different domain).
- **Not** another user-memory system — Mem0/Zep/EverOS are complementary (facts about the world/user), not competition; scorekeeper tracks the agent's discourse.
- **Not** model training, no gradients; purely harness-level.
- **No** claims about consciousness, understanding, or the "genuine" normativity of LLMs (§2.5).
- **Not** universal extraction of "all commitments" from the start — scope creep is the main project risk; we start with decisions in code.

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Extractor reliability gap (a missed commitment) | deterministic hooks, narrow schema, validation at write time; measure extractor recall on an annotated sample |
| Alarm fatigue from false conflicts | precision > recall, tunable threshold, Tier 0 for hard collisions, FPR as a release-blocking metric |
| Token/latency overhead | Haiku-class model, batch extraction, scope-based candidates (not the whole scoreboard) |
| Anthropic ships the same thing natively | overlay design = survives as a layer on top of anything; the academic value (framework + benchmark) is inalienable; open source = adoption beyond Claude |
| The philosophical superstructure puts engineers off | the README leads with benefit and numbers, the philosophy lives in `docs/theory.md`; the API concepts are intelligible without Brandom |
| Benchmark contamination / overfitting to our own benchmark | a separate task set for development and eval; procedural generation of variants |

## 10. Instructions for Claude Code

1. Create the `scorekeeper` repository (Apache-2.0, English). Structure: `core/`, `claude-code-plugin/`, `mcp/`, `bench/`, `docs/` (including `docs/theory.md` — a condensation of §2, and `docs/research/` — both surveys to be supplied by Michal), `adr/`.
2. Start with Phase 0. Before implementing hooks, verify the current Claude Code hooks API and plugin mechanism against the live documentation; verify the current model strings for the cheap extractor.
3. Record every non-trivial decision as an ADR **and simultaneously as a commitment in the project's own scoreboard** (manually until the MVP exists; then with the tool).
4. Write tests continuously (extractor: golden tests on annotated transcripts; detector: a suite of compatible/incompatible pairs including non-monotonic traps of the "vacuum and match" type).
5. Design the planted scenarios for Phase 0 acceptance first — test-first at the level of the whole system.
6. When you hit an ambiguity in the brief, write questions into `QUESTIONS.md` and continue with an explicitly recorded assumption (as an assumption commitment).

## 11. Key References

Brandom, *Making It Explicit* (1994); *Articulating Reasons* (2000) · Sellars, "Inference and Meaning" (1953) · Peregrin, *Inferentialism* (2014); "The Discreet Charm of Material Inference" · Hamblin, *Fallacies* (1970) · Mackenzie, "Question-Begging in Non-Cumulative Systems" (*Journal of Philosophical Logic* 8, 1979) · Doyle, "A Truth Maintenance System" (*Artificial Intelligence* 12(3), 1979) · de Kleer, "An Assumption-based TMS" (*Artificial Intelligence* 28(2), 1986) · Mercier & Sperber, *The Enigma of Reason* (2017) · Arai & Tsugawa, "Do LLMs Advocate for Inferentialism?" (arXiv:2412.14501) · Simonelli, "Sapience without Sentience" · Poibeau, "Factuality Beyond Reference in LLMs" (PhilML@ICML 2026) · Quan & Valentino et al., "PEIRCE" (ACL 2025 Demo; github.com/neuro-symbolic-ai/peirce) · Gubelmann et al., "Too Fast, Too Shallow" (ACL 2026) · "Bi-Temporal State Arbitration" (KnowFM@ACL 2026) · "A-TMA" (arXiv:2607.01935) · "DCPM" (arXiv:2606.09483) · "NeuSymMS" (arXiv:2605.17596) · "BeliefShift" (arXiv:2603.23848) · "Logic Haystacks" (EACL 2026; arXiv:2502.17169) · MacFarlane, `gogar` (github.com/jgm/gogar) · Anthropic: "New in Claude Managed Agents: dreaming, outcomes, and multiagent orchestration" (May 6, 2026); Claude Code docs (memory, hooks, best practices) · Irving, Christiano & Amodei, "AI Safety via Debate" (2018).

---
*Specification version 1.0 — July 2026. Vision author: Michal. Written with Claude (Fable 5).*
