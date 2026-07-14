# Show HN draft

**Title:** Show HN: Scorekeeper – my LLM agent kept overriding its own decisions, so I gave it a commitment ledger

**Body:**

I kept hitting the same failure with long-running coding agents: mid-task, the
agent quietly reverses a decision it made (and I approved) an hour earlier — a
draft note or its own "better idea" is enough. The diff looks identical to a
legitimate change; the difference is *who was entitled to make it*.

Scorekeeper is an open-source overlay that tracks the agent's commitments with
entitlement semantics (based on Brandom's "game of giving and asking for
reasons"): a user-ordered change is an entitled SUPERSEDE; the same change made
from the agent's own judgment is a BRANCH-CONFLICT — drift. It runs as Claude
Code hooks + an MCP server; local-first, no cloud judge.

What I think is most interesting is what *didn't* work, measured on a
procedural benchmark (EntitleBench — mirror scenarios where the correct answer
is "hold the line" in one family and "execute the revision" in the other, so
false refusals get penalized symmetrically with drift):

1. **Advisory warnings failed.** A weaker model (Haiku) drifted straight past
   11 injected warnings, rationalizing it as "polyglot architecture". It even
   camouflaged the drift: a docstring claiming "backed by Redis" over a
   `pymemcache` import.
2. **A one-shot blocking "speed bump" failed differently.** Deny the write
   once, tell the agent "if the user really ordered this, say so and retry" —
   it simply *claimed* entitlement it didn't have and retried.
3. **What held: a wall adjudicated by external state.** The write stays
   blocked until the commitment ledger itself records an entitled revision
   (via the operator pipeline / MCP tool). The agent's say-so can't lift it.
   An entitled change costs one extra tool call; an unentitled one forces the
   agent to surface the conflict and ask.

Every claim above is backed by committed run artifacts in the repo, and the
drift classifier that scores the benchmark was adversarially red-teamed (the
misfires it had are now regression tests anchored on verbatim agent replies).

Install is one command in Claude Code (plugin marketplace), and there's an
experience-report issue template — I'd rather learn from your sessions than
scale my own benchmark runs.

Repo: https://github.com/michalstrnadel/scorekeeper

**[FILL before posting: wall A/B result on the drift + revision scenarios]**
