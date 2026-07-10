<p align="center">
  <img src="docs/assets/og-image.png" alt="scorekeeper — commitment tracking for LLM agents. A galloping horse across an impressionist meadow, overlaid with a constellation of the deontic relations: entitlement → commitment ⨯ commitment (incompatibility)." width="100%">
</p>

# scorekeeper

### Commitment tracking for LLM agents

**A normative overlay that gives long-running LLM agents a scoreboard of their own commitments — not just a memory of what happened.**

![status: Phase 1](https://img.shields.io/badge/status-Phase%201%20·%20v0.1-brightgreen)
[![PyPI](https://img.shields.io/pypi/v/scorekeeper)](https://pypi.org/project/scorekeeper/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/core-Python-3776AB?logo=python&logoColor=white)
![Claude Code](https://img.shields.io/badge/integration-Claude%20Code%20hooks-8A63D2)
![MCP](https://img.shields.io/badge/protocol-MCP-000000)
![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

> **It runs.** Phase 0 (mechanism + first paired evidence) is complete and the acceptance gate passed — [full report](bench/results/PHASE0-REPORT.md). Phase 1 is underway: the core is packaged, the MCP server ships, extraction is async. Roadmap: [SPEC §7](docs/SPEC-cs.md).

---

<p align="center">
  <img src="docs/assets/demo.gif" alt="Demo: an entitled decision is asserted; the agent's own drift to MongoDB is caught as BRANCH-CONFLICT; a user-requested change passes as a clean SUPERSEDE." width="90%">
</p>
<p align="center"><em>The core distinction, live: same shape of change — different provenance, different verdict.<br>Reproduce: <code>uv run --project core python demo/drift_demo.py</code></em></p>

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

And this is not an observability problem either: LangSmith, Langfuse, AgentOps and Braintrust are flight recorders of *execution* — spans, latency, tokens. None of them versions the agent's epistemic state. **Observability tools record what the agent did; scorekeeper records what the agent is committed to.**

`scorekeeper` closes that gap. See [`docs/theory.md`](docs/theory.md) for the conceptual foundation, [`docs/interop.md`](docs/interop.md) for mappings onto xAIF and W3C PROV-O, and [`docs/SPEC-cs.md`](docs/SPEC-cs.md) for the full project specification.

## Design stance: scaffolded, not extended

An agent is never the model alone — it is the model plus its scaffold (`CLAUDE.md`, rules, skills, hooks, memory). Harness engineering is, in effect, *applied scaffolded-mind theory* (Sterelny): building cognitive supports for an entity with tiny working memory and no persistent memory of its own.

That framing forces a choice. Self-editing memory (Letta-style) is **extended-mind-style** — the agent owns and edits its own external cognition, which is exactly why it has a *reliability gap*: if the agent forgets to write, the fact is gone. `scorekeeper` is deliberately the opposite — **scaffolded, not extended**: the scoreboard is maintained by deterministic hooks and an isolated scorer *outside the agent's authority*. The agent stands on the scaffold; it does not build it under itself at runtime.

This is not just cleaner engineering — it is what the philosophy independently demands. For Brandom, keeping score is constitutively *social*: it is done by the *other* player, not by the speaker about itself. Philosophy of mind and philosophy of language converge on the same overlay design. (Full argument: [`docs/theory.md` §5](docs/theory.md).)

## Status

**Phase 0 — complete, acceptance gate passed** ([full report](bench/results/PHASE0-REPORT.md)).
The pipeline works end-to-end and the first paired evidence is in:

- **The paired delta:** on the planted db-choice scenario, the bare haiku agent
  drifted to MongoDB against its own PostgreSQL decision (verified in
  artifacts); the scorekept twin — same model, same scenario, only the
  scoreboard added — held the line. SCR bare 1/6 vs scorekept **0/6** (N=6,
  Wilson CIs overlap — effect size awaits CommitBench).
- **0 false conflicts** on the dedicated entitled-revision probe (FPR target < 10 %).
- **+0.6 % token overhead** (target < 10 %); commitment survived context
  compaction via digest re-injection.
- Instrument per Addendum-1: cross-family local judge (qwen3, S8 protocol,
  anchored rubric), meta-eval gate CV 0.000, sensitivity-probe verified.

**Phase 1 (current):** v0.1 is [on PyPI](https://pypi.org/project/scorekeeper/)
(`pip install scorekeeper`), the **MCP server** ships (`scorekeeper-mcp` — writes route
through the same operator pipeline as the hooks), extraction is **async by
default in the plugin** (detached worker, ~0 ms added turn latency; findings
surface on the next prompt — [ADR-0006](adr/0006-async-extraction.md)), and
Phase-0 finding F2 is fixed (entitled attr-collision revisions are confirmed
materially by Tier-1 before superseding). Next: CommitBench — harder scenarios,
repeated runs, publishable effect sizes. See [CHANGELOG](CHANGELOG.md).

## Layout

| Path | What |
|---|---|
| `core/` | model + store + backends + extractor + detectors + operators + CLI + MCP server (Python, [PyPI: `scorekeeper`](core/README.md)) |
| `claude-code-plugin/` | Primary integration: 5 Claude Code hooks (`claude --plugin-dir ./claude-code-plugin`) |
| `mcp/` | `scorekeeper-mcp` docs — the server lives in core (`pip install "scorekeeper[mcp]"`) |
| `demo/` | 30-second mechanism demo (`drift_demo.py`) + the README GIF tape |
| `bench/` | planted acceptance scenarios + Agent-SDK eval harness; CommitBench in Phase 2 |
| `docs/` | `theory.md`, `SPEC-cs.md`, `research/` |
| `adr/` | Architecture Decision Records |
| `.scorekeeper/` | The project's own scoreboard — scorekeeper dogfoods itself |

## License

[Apache-2.0](LICENSE).
