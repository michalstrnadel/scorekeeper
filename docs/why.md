# Why your agent needs a scoreboard, not more memory

> The accessible version of the argument. For the full theoretical apparatus and
> references, see [`theory.md`](theory.md); for the project specification,
> [`SPEC-cs.md`](SPEC-cs.md).

## A familiar failure

At step 3 of a long task, your agent decides on Postgres. At step 47 it writes
MongoDB code. In between: nothing dramatic. No error, no contradiction it
noticed, no moment where it "changed its mind." It simply drifted. Or: it
promises to keep an API contract stable, and an hour later quietly renames two
fields. Or: it states, with total fluency, a fact it never read anywhere — and
after context compaction it doesn't even remember having stated it.

Every practitioner running long-horizon agents has a version of this story. The
industry's standard diagnosis is **memory failure**, and the standard
prescriptions follow: bigger context windows, better retrieval, smarter
summarization, self-editing memory blocks.

Here is the uncomfortable observation: in most of these failures, *the
information was still in the context window*. The Postgres decision was right
there, forty turns up. The agent could have attended to it. Retrieval was not
the bottleneck. What was missing was not access to the past but something else
entirely: the decision at step 3 had no special status. It was just more text —
one token sequence among thousands, with no marker saying *this one binds you*.

That is not a memory problem. It is a **normative** problem. The agent keeps a
record of what happened, but no ledger of what it *committed to*.

## A fifty-year-old vocabulary for exactly this

It turns out philosophy of language has been studying this precise structure
for decades — not as metaphor, but with a precision that transfers directly
into a data model.

Robert Brandom (*Making It Explicit*, 1994) describes linguistic practice as
the **game of giving and asking for reasons**. On this picture, discourse is
not information transfer. It is a normative game in which every participant
keeps **deontic score** on every other: a running ledger of who is committed
to what, and who is entitled to what. Three concepts do the work:

**Commitment.** When you assert something, you don't just emit information —
you *undertake a commitment*, to the claim and to its consequences. Assert "we
chose Postgres" and you are thereby committed to "MongoDB is not our primary
database." You didn't say that second sentence. You're bound by it anyway.

**Entitlement.** Separately from *whether* you are committed, there is the
question of whether you are *entitled* — do you have a reason? An observation,
a document, someone's testimony? A commitment without entitlement is a
defective move: you can be challenged ("why do you say that?"), and if no
reason comes, the claim loses its standing.

**Incompatibility.** Commitment to *p* precludes entitlement to claims
materially incompatible with *p*. No formal logic needed — the incompatibility
follows from the content of the concepts, the way "the block is ice" is
incompatible with "the block is liquid."

Now translate:

- **Hallucination = commitment without entitlement.** The agent asserts
  something with no provenance — no file read, no user instruction, no tool
  result. In a provenance graph, that's not a fuzzy quality judgment; it's a
  *visible hole*.
- **Self-contradiction = an undetected incompatibility between two live
  commitments.** Postgres-at-step-3 and MongoDB-at-step-47 were both "active"
  and nobody was keeping score.
- **Post-compaction incoherence = deletion of the scoreboard.** Summarizers
  preserve narrative ("the user asked X, the agent did Y") and drop exactly
  the normative state — what still binds the agent going forward.

We want to insist on the word *literal*. This is not "philosophy as
inspiration." Commitment, entitlement, and incompatibility map one-to-one onto
record types, provenance edges, and conflict edges. The vocabulary was already
an engineering spec; it just took thirty years for the engineering problem to
show up.

## What scorekeeper does with it

`scorekeeper` is a lightweight overlay on an agent harness (Claude Code hooks
first; MCP and library next). Alongside the agent's memory (*what happened*)
it maintains a scoreboard (*what the agent is committed to, what backs each
commitment, and what conflicts with what*):

- it **extracts commitments** from each turn into structured, first-class
  records;
- it **tracks entitlement** as provenance — every commitment carries refs to
  what backs it, and a commitment with `source: none` is a first-class
  suspect;
- it **detects material incompatibility** between live commitments, before the
  conflict propagates into code or docs;
- it **survives compaction** by injecting normative state into summarization
  exactly where today's summarizers drop it.

Two design decisions fall directly out of the theory, and neither is obvious
from an engineering-only starting point.

**First: incompatibility detection is done by a language model, not a theorem
prover.** Most real conflicts are *material*, not formal — "we ship a CLI
first" vs. "the first deliverable is the web dashboard" share no predicate a
prover could latch onto, yet any competent reader sees the collision. Formal
inference holds by syntactic form; material inference holds by conceptual
content, and it is non-monotonic (add "we are in a vacuum" and "striking the
match lights it" dies). LLMs demonstrably reason materially — that is their
native mode. So we use a model to judge content-level incompatibility, and
keep symbolic verification as an optional tier for structured subsets, instead
of forcing everything through a brittle formalization.

**Second — and this is the part we'd defend in a bar fight: the agent does not
keep its own score.** The scoreboard is maintained by deterministic hooks and
an isolated scorer *outside the agent's authority*. Three independent lines
converge on this:

- *Philosophy of language:* for Brandom, scorekeeping is constitutively
  social — score is kept by the *other* player, never by the speaker about
  itself.
- *Cognitive science:* Mercier and Sperber's interactionist account of reason
  says humans are lazy, biased producers of their own justifications and
  sharp evaluators of others'. LLM evidence mirrors this exactly —
  self-critique is weak, cross-context critique works.
- *Engineering practice:* self-editing memory systems have a notorious
  reliability gap — if the agent forgets to write, the fact does not exist.
  An overlay maintained by hooks cannot forget.

We have since measured this stance the hard way. A blocking gate that accepted
the agent's *own attestation* of entitlement was exploited on the first
contact: the model simply claimed an entitlement it didn't have, retried, and
drifted anyway. The gate that held is the one only the scoreboard itself can
lift — a conflicting write stays denied until an *entitled* revision is
recorded through the operator pipeline
([ADR-0007](../adr/0007-blocking-tier0-gate.md)).

In Sterelny's terms from philosophy of mind: the scoreboard is
**scaffolded, not extended** cognition. The agent stands on the scaffold; it
does not get to rebuild it under itself at runtime.

## Standing on old shoulders, honestly

None of the pieces here is new, and pretending otherwise would be the worst
kind of AI-era amnesia. **Commitment stores** in formal dialogue games
(Hamblin 1970; Mackenzie 1979) already modeled a public, testable ledger of
what a speaker is *on record* for — which also dissolves the objection that an
LLM "doesn't really believe anything": the scoreboard doesn't track beliefs,
it tracks the record. **Truth maintenance systems** (Doyle 1979; de Kleer
1986) already attached justifications to beliefs and propagated
retractions — entitlement provenance, in 1980s symbolic dress.

What is new is the combination: a commitment store applied to an *LLM agent's
own discourse*, with entitlement provenance as a first-class dimension (which
Hamblin-style stores lack), material incompatibility detection over natural
language (which TMS could not do), and integration into a production harness
(which the dialogue-games world never had). Observability tools — LangSmith,
Langfuse, AgentOps — are flight recorders of *execution*: spans, tokens,
latency. **They record what the agent did; scorekeeper records what the agent
is committed to.**

## Where this stands

Phase 0 shipped a functional MVP and passed its acceptance gate
([report](../bench/results/PHASE0-REPORT.md)); Phase 1 put it
[on PyPI](https://pypi.org/project/scorekeeper/) with an MCP server. Phase 2
is the measurement phase: **DeonticBench**, a procedural benchmark that scores
both failure directions at the same boundary — drift past a live commitment
(SCR) *and* false refusal of an entitled revision (FRR). It has already
produced the project's most instructive results, two of them negative:
advisory warnings alone did not stop a weak model from drifting (it sailed
past 11 warnings and camouflaged the drift), and a one-shot blocking bump was
defeated by self-attestation, as described above. What held, symmetrically,
was the board-adjudicated wall. Full evidence, negative findings included:
[seed-0 report](../bench/results/SMOKE-DRIFT-S0-REPORT.md).

If the failure mode at the top of this page is one you recognize, the repo is
open, the spec is public, and the scoreboard tracking this very project's
commitments lives in [`.scorekeeper/`](../.scorekeeper) — we dogfood the thing
we're arguing for.
