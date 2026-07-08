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

## 5. Honesty of the frame

Brandom serves the project as a design vocabulary and a source of non-trivial architectural decisions (entitlement as a first-class dimension; material detection; explicitation) — not as dogma. Where philosophical fidelity collides with engineering usefulness, usefulness wins and the deviation is documented (see the ADR process). The project claims **nothing** about consciousness, understanding, or "genuine" agent normativity — Poibeau's remark that an agent without sanctions merely simulates normativity holds; it is irrelevant to the engineering value of the scoreboard.

---

*Full references: see `docs/SPEC-cs.md` §11.*
