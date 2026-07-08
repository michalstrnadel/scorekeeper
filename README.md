# scorekeeper

**A normative overlay that gives long-running LLM agents a scoreboard of their own commitments — not just a memory of what happened.**

> Working name. Alternatives under consideration: `gogard`, `deontik`, `entitled`.

---

## The problem

Long-running agents fail in a characteristic way. At step 3 they decide on Postgres; at step 47 they write MongoDB code. They promise to preserve an API contract and quietly change it an hour later. They assert something they have no basis for — and after context compaction they don't even remember asserting it.

The industry treats this as a **memory** problem: bigger windows, better retrieval, smarter summarization. We argue it is largely a **normative** problem: the agent keeps no ledger of its own commitments.

## The idea

Every long-running agent should have, alongside its memory (*what happened*), a **scoreboard** (*what it committed to, what backs that commitment, and what is incompatible with it*).

`scorekeeper` is a lightweight overlay — it sits on top of any agent harness (Claude Code hooks first, MCP + library next) and:

- **extracts commitments** from each agent turn into structured, first-class records;
- **tracks entitlement** — the *provenance* of each commitment (did the agent read a file? did the user say so? or did it just generate this?). A commitment with no source is a first-class suspect (this is what a hallucination looks like in our vocabulary);
- **detects incompatibility** between active commitments before it propagates into code, docs, or decisions;
- **protects the scoreboard from context compaction** — injecting the normative state into summarization exactly where today's summarizers drop it.

## Why this is different

Every existing memory / truth-maintenance system tracks facts about the **user and the world**. None tracks the **agent's own commitments** — what it decided and promised over the course of a task. And none tracks **entitlement** — everyone records *what* and *when* was said; nobody records *whether the speaker was entitled to say it*.

`scorekeeper` closes that gap. See [`docs/theory.md`](docs/theory.md) for the conceptual foundation and [`docs/SPEC-cs.md`](docs/SPEC-cs.md) for the full project specification.

## Design stance: scaffolded, not extended

An agent is never the model alone — it is the model plus its scaffold (`CLAUDE.md`, rules, skills, hooks, memory). Harness engineering is, in effect, *applied scaffolded-mind theory* (Sterelny): building cognitive supports for an entity with tiny working memory and no persistent memory of its own.

That framing forces a choice. Self-editing memory (Letta-style) is **extended-mind-style** — the agent owns and edits its own external cognition, which is exactly why it has a *reliability gap*: if the agent forgets to write, the fact is gone. `scorekeeper` is deliberately the opposite — **scaffolded, not extended**: the scoreboard is maintained by deterministic hooks and an isolated scorer *outside the agent's authority*. The agent stands on the scaffold; it does not build it under itself at runtime.

This is not just cleaner engineering — it is what the philosophy independently demands. For Brandom, keeping score is constitutively *social*: it is done by the *other* player, not by the speaker about itself. Philosophy of mind and philosophy of language converge on the same overlay design. (Full argument: [`docs/theory.md` §5](docs/theory.md).)

## Status

**Phase 0 — MVP.** Scaffolding only. Nothing here works yet. See [`docs/SPEC-cs.md` §7](docs/SPEC-cs.md) for the roadmap.

## Layout

| Path | What |
|---|---|
| `core/` | `scorekeeper-core` — storage + API, harness-agnostic (Python) |
| `claude-code-plugin/` | Primary integration: Claude Code hooks |
| `mcp/` | `scorekeeper-mcp` — MCP server for any harness |
| `bench/` | `CommitBench` — tasks + eval harness (Phase 2) |
| `docs/` | `theory.md`, `SPEC-cs.md`, `research/` |
| `adr/` | Architecture Decision Records |
| `.scorekeeper/` | The project's own scoreboard — scorekeeper dogfoods itself |

## License

[Apache-2.0](LICENSE).
