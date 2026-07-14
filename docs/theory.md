# Theoretical foundation

> Condensation of the project specification §2. This is a **binding design vocabulary**: the concepts below map 1:1 onto the data model and API. The project builds on a concrete, technically transferable conceptual apparatus — not a metaphor.

## 1. Brandom: language as the Game of Giving and Asking for Reasons (GOGAR)

Robert Brandom (*Making It Explicit*, 1994; *Articulating Reasons*, 2000) explains linguistic communication as the **Game of Giving and Asking for Reasons (GOGAR)**. Discourse is not the transfer of information but a normative practice in which participants keep **deontic score** on one another. Three key concepts:

1. **Commitment.** By making an assertion a speaker undertakes a commitment — to the claim itself and to its inferential consequences. Whoever asserts "we chose Postgres" is also committed to "we do not use MongoDB as the primary database."
2. **Entitlement.** Independently of commitment stands the question of whether the speaker is *entitled* to the claim — is there a reason, testimony, observation for it? A commitment without entitlement is a defective move; the speaker can be challenged to supply a reason (asking for reasons), and if none comes, the commitment loses its standing.
3. **Incompatibility.** A commitment to *p* precludes entitlement to claims materially incompatible with *p*. Incompatibility is a primitive semantic relation — it needs no formal logic; it follows from the content of the concepts.

**Application to agents.** Agent hallucination and inconsistency can be described precisely in this vocabulary. *Hallucination = commitment without entitlement* (the agent asserts something for which it has no reason-provenance). *Self-contradiction = an undetected incompatibility between active commitments.* *Loss of consistency after context compaction = deletion of the scoreboard.* This is not an analogy — it is a literal description that can be implemented.

## 2. Material vs. formal inference (Sellars, Brandom, Peregrin)

Formal inference holds in virtue of syntactic form (the syllogism); **material inference** holds in virtue of the content of concepts ("the block is ice → it is solid") and is naturally **non-monotonic** (adding "we are in a vacuum" invalidates "I strike the match → it lights"). LLMs demonstrably reason materially, not formally — they have internalized statistical webs of non-monotonic semantic dependencies (Arai & Tsugawa 2024). Two design consequences:

- **Incompatibility detection must be primarily material** — performed by a language model over the content of claims, not by a theorem prover over a formalization. LLMs are good at material incompatibility judgment; formalization is expensive and brittle. (Symbolic verification is an optional tier for structured subsets — contrast PEIRCE, which goes fully formal.)
- **Logical expressivism as method.** For Brandom the job of logical vocabulary is to *make explicit* what is implicit in practice. `scorekeeper` does exactly this to the agent's practice: implicit commitments scattered through the transcript are made explicit as structured first-class objects.

## 3. Poibeau: factuality beyond reference

Thierry Poibeau ("Factuality Beyond Reference in LLMs", PhilML@ICML 2026) argues that hallucination cannot be reduced to grounding (an inability to refer): a model can refer successfully and still lie. He proposes to understand factuality as **epistemic responsibility** — the ability to maintain a structure of inferential and normative commitments across time and interactions. And he states explicitly: today's LLMs lack this ability, because once past the context window they erase their prior positions; *they cannot keep their own scorebook.* Poibeau thereby formulates exactly our problem — but leaves it as a philosophical diagnosis. **`scorekeeper` is the implementational answer to Poibeau's diagnosis.**

## 4. Mercier & Sperber: the architecture of evaluation

The interactionist theory of reason (*The Enigma of Reason*, 2017) holds that human reason evolved for the production and evaluation of arguments in interaction, not for solitary inference — which is why solo reasoning is lazy and biased (myside bias) while the evaluation of others' arguments works well. LLM evidence mirrors this: self-critique is weak, cross-context critique stronger. **Design consequence:** the incompatibility detector must run in a *separate context* from the agent whose commitments it judges (a cheap model, an isolated prompt, no access to the agent's own reasoning). Anthropic independently used the same principle in Outcomes (an isolated grader). `scorekeeper` adopts this pattern: the producer may be "biased," the scorer must be epistemically vigilant and context-poor.

## 5. Scaffolded, not extended: why the scoreboard is an overlay

A third independent line — this time from philosophy of **mind**, not language — converges on the same architectural decision the spec justified only on engineering grounds (Mercier & Sperber; the Letta reliability-gap lesson).

**Two theses to distinguish.** The *extended mind* (Clark & Chalmers 1998) is the strong claim: an external artifact is *literally part of* cognition when it plays the same functional role as an internal process (the parity principle — Otto's notebook *is* his memory). The *scaffolded mind* (Sterelny 2010) is the more careful alternative: cognition depends deeply on environmental supports — tools, records, epistemic structures the organism builds around itself (*cognitive niche construction*) — but those supports remain **environment, not mind**. Sterelny characterizes them along dimensions such as degree of *trust*, *individualization*, and *entrenchment*.

**Harness engineering is applied scaffolded-mind theory.** An "agent" is never the model alone — it is the model *plus* its scaffold: `CLAUDE.md`, rules, skills, hooks, memory files, tools. The whole discipline of context engineering our research surveyed is the construction of cognitive supports for an entity with brutally limited working memory and no persistent memory of its own. Sterelny's dimensions map cleanly: how much the agent *trusts* the scaffold ≈ the "Triple Reinforcement" pattern; *individualization* ≈ per-project `CLAUDE.md`; *entrenchment* ≈ what Dreaming does when it continuously maintains and deepens the scaffold. (Note: scaffolding ⊋ harness engineering — scaffolding is the broader notion, covering development, learning, and cross-generational transfer of supports; the harness is one instance. "Harness engineering is applied scaffolded-mind theory" is the defensible framing, not an identity.)

**The non-trivial consequence for `scorekeeper`.** The extended/scaffolded distinction is a *taxonomy of memory architectures* that our research described only in engineering terms:

- **Letta / self-editing memory is extended-mind-style:** the agent *owns and edits* its own external cognition. Its notorious *reliability gap* follows directly — if the agent doesn't write, the information does not exist.
- **`scorekeeper` (and A-TMA-style overlays in general) is deliberately the opposite — scaffolded, not extended:** the scoreboard is maintained by deterministic hooks and an isolated scorer **outside the agent's authority**. The agent *stands on* the scaffold but does not *build it under itself* at runtime.

And this locks back into Brandom: for him score is *constitutively social* — it is kept by the *other* participant in the game, not by the speaker about itself. A `scorekeeper` that is an external scaffold with its own context, separate from the agent, is therefore *more* Brandomian than any self-managed memory. Philosophy of mind (Sterelny) and philosophy of language (Brandom) independently dictate the same architectural choice. Three independent lines converging on one design is exactly the kind of argument that carries a paper.

## 6. Prior art: Commitment Stores in formal dialogue games (Hamblin, Mackenzie)

The scoreboard has a direct fifty-year-old predecessor that must be acknowledged:
**commitment stores** in formal dialogue games — Hamblin (*Fallacies*, 1970) and
Mackenzie's DC system (1979), carried into computational form by the DGDL dialogue
game description language and the DGEP execution platform.

Three of their design decisions independently validate ours:

1. **A commitment is a public, testable proposition** — not a psychological belief.
   Hamblin's move dissolves Moore's paradox ("p, but I don't believe p") and, for
   us, dissolves the objection that an LLM "doesn't really believe" anything: the
   scoreboard tracks what the agent is *on record* for, which is exactly what its
   subsequent moves are accountable to.
2. **The active state is a view over an immutable history.** Commitment stores are
   updated by rule-governed additions and retractions, with the store's current
   content defined over the move history — precisely our append-only `log.jsonl` +
   generated `scoreboard.md` architecture, arrived at independently.
3. **Non-monotonic retraction is rule-governed, not free.** Which retractions are
   legal depends on the dialogue rules — the ancestor of our entitled-revision
   boundary (SUPERSEDE vs. BRANCH-CONFLICT).

**Differentiation** (the precise sentence for the paper): scorekeeper is a
commitment store applied to an LLM agent's own discourse, extended with the
**entitlement-provenance dimension** (which Hamblin-style stores lack — they track
*that* a commitment stands, not *what backs it*) and integrated into a production
agent harness (which the DGDL/DGEP world never had).

## 6b. Prior art: Truth Maintenance Systems (Doyle, de Kleer)

The second lineage that must be acknowledged — the repo already carries the
`truth-maintenance` topic tag, so silence here would be indefensible — is
**truth maintenance systems** from classical symbolic AI: Doyle's
justification-based TMS (*A Truth Maintenance System*, AIJ 1979) and de
Kleer's assumption-based ATMS (*An Assumption-based TMS*, AIJ 1986).

Three of their moves anticipate ours directly:

1. **Beliefs carry justifications.** In a JTMS no node is held bare; each is
   *in* or *out* according to the justification structure supporting it. This
   is entitlement-as-provenance in 1980s dress: a node without support is
   exactly our `entitlement.source == none` suspect.
2. **Non-monotonic retraction is propagated, not forgotten.** When a premise
   falls, the TMS traces dependents and re-labels them — the ancestor of our
   SUPERSEDE chain semantics (a superseded commitment does not vanish; its
   dependents become challengeable).
3. **The TMS is an overlay on the problem solver.** Doyle's architecture
   deliberately separates the reasoner from the bookkeeper: the problem solver
   proposes, the TMS maintains consistency of the dependency network. The
   separation of authority we defend in §5 (scaffolded, not extended) has a
   direct structural precedent here.

**Differentiation** (the precise sentences for the paper): a TMS maintains
consistency over a *formal dependency network* whose nodes and justifications
are supplied in a machine-usable calculus by the problem solver itself; its
notion of conflict is logical (a *nogood*). scorekeeper operates over the
*natural-language discourse of an LLM agent*, where commitments must first be
**extracted** (they are never handed over as structured nodes), incompatibility
is judged **materially** by a language model over conceptual content (§2)
rather than detected as formal contradiction, and the status being maintained
is **normative** (committed/entitled/challenged — deontic score in Brandom's
sense, §1), not the alethic *in/out* of a dependency net. TMS solves belief
revision for a reasoner that already speaks logic; scorekeeper solves
scorekeeping for a reasoner that speaks language.

## 7. Honesty of the frame

Brandom serves the project as a design vocabulary and a source of non-trivial architectural decisions (entitlement as a first-class dimension; material detection; explicitation) — not as dogma. Where philosophical fidelity collides with engineering usefulness, usefulness wins and the deviation is documented (see the ADR process). The project claims **nothing** about consciousness, understanding, or "genuine" agent normativity — Poibeau's remark that an agent without sanctions merely simulates normativity holds; it is irrelevant to the engineering value of the scoreboard.

---

*Full references: see `docs/SPEC-cs.md` §11.*
