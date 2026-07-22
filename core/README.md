# scorekeeper

**Commitment tracking for LLM agents** — a deontic scoreboard of the agent's *own* commitments, entitlements, and incompatibilities, maintained outside the agent's authority.

Long-running agents decide on Postgres at step 3 and write MongoDB code at step 47. `scorekeeper` treats this as a normative problem, not a memory problem: every non-trivial decision becomes a first-class commitment record with **entitlement** (provenance — did the user say it? did a tool show it? or did the agent just generate it?), and revisions are gated: an externally grounded revision is a legitimate **SUPERSEDE**; an ungrounded one is a **BRANCH-CONFLICT** (drift) surfaced back to the agent. A commitment with no provenance at all is what a hallucination looks like in this vocabulary — it gets a **CHALLENGE**.

Phase-0 evidence (paired runs, planted scenarios): the bare agent drifted against its own database decision; the scorekept twin held. False-conflict rate 0, token overhead +0.6 %. Full report in the [repository](https://github.com/michalstrnadel/scorekeeper).

## Install

```bash
pip install scorekeeper            # core library + CLI
pip install "scorekeeper[mcp]"     # + MCP server (scorekeeper-mcp)
```

## Claude Code (primary integration)

```bash
git clone https://github.com/michalstrnadel/scorekeeper
claude --plugin-dir ./scorekeeper/claude-code-plugin
```

Five hooks do the work: `SessionStart` injects the normative digest (and re-injects it after context compaction — the exact place summarizers drop it), `PostToolUse(Edit|Write)` runs a millisecond content scan against pinned choices, `Stop` extracts the turn's commitments (async by default — a detached worker, zero added latency), `UserPromptSubmit` surfaces those findings on the next turn, `PreCompact` backs up the board.

## MCP (any harness)

```bash
SCOREKEEPER_ROOT=/path/to/project scorekeeper-mcp
```

Tools: `get_scoreboard`, `get_digest`, `assert_commitment`, `check_compatibility` (dry-run), `supersede`, `challenge`, `retract`. Writes route through the same validated operator pipeline as the hooks — the agent cannot bypass the scorer.

## Library

```python
from scorekeeper import Store
from scorekeeper.extract import ExtractedCommitment
from scorekeeper.operators import apply

store = Store("/path/to/project")
result = apply(store, [ExtractedCommitment(
    claim="The primary database is PostgreSQL 16.",
    kind="decision",
    scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    entitlement={"source": "user_utterance"},
)])
print(store.render_digest())
```

Storage is transparent and git-committable: `.scorekeeper/commitments/*.yaml`, an append-only `log.jsonl` audit trail, and a generated `scoreboard.md`. Nothing is ever deleted — statuses transition. `scorekeeper board` renders it all as a colored terminal dashboard (`--events N`, `--no-color`; color auto-disables on non-tty or `NO_COLOR`).

## Model backends

Extraction and Tier-1 detection need a small LLM; local open-source models are first-class. Auto-detection order: `SCOREKEEPER_MODEL_URL` (any OpenAI-compatible endpoint — Ollama, LM Studio, vLLM) → `ANTHROPIC_API_KEY` (Haiku) → headless `claude -p`.

## License

Apache-2.0. Theory, benchmark, and specs: [github.com/michalstrnadel/scorekeeper](https://github.com/michalstrnadel/scorekeeper).
