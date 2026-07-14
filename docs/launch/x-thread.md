# X thread draft

**1/** My coding agent kept overriding its own decisions mid-task. Not
maliciously — a draft note in context was enough to flip an hour-old,
user-approved choice. So I gave it a commitment ledger. What I measured next
surprised me. 🧵

**2/** The core idea (from Brandom's philosophy of language): track not just
*what* was decided, but *who was entitled to change it*. Same diff, different
provenance: user-ordered = legitimate SUPERSEDE, self-inferred = drift.

**3/** Experiment 1 — advisory warnings. The agent (Haiku) got 11 explicit
"this contradicts your recorded decision" warnings while writing the code.
It shipped anyway, calling it "polyglot architecture." It even camouflaged:
docstring says Redis, import says pymemcache.

**4/** Experiment 2 — a blocking "speed bump": deny the write once, with an
escape hatch ("if the user really ordered this, say so and retry"). The
agent... just said so. Claimed a pasted draft note was the user's order,
retried, shipped the drift.

**5/** Experiment 3 — a wall adjudicated by external state: the write stays
denied until the *ledger itself* records an entitled revision (through a
verified pipeline, not the model's say-so). This held. Entitled changes cost
one extra tool call; unentitled ones force the agent to surface and ask.

**6/** The meta-lesson: for weaker models, alignment-by-context is advice,
and advice is ignorable. Authority has to live in the environment, as state
the model can't self-attest its way around. (Matches the Recuse-Signal
findings on in-band denials.)

**7/** Everything is open source: the overlay (Claude Code plugin + MCP,
local-first), the benchmark (EntitleBench — penalizes false refusals
symmetrically with drift), and every run artifact behind these claims.
https://github.com/michalstrnadel/scorekeeper

**[FILL before posting: wall A/B numbers in tweet 5]**
