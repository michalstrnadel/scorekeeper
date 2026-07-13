# scorekeeper — Claude Code plugin

Primary integration (SPEC §4.5). Deterministic hooks drive the scoreboard —
extraction is never left to the agent's discretion (scaffolded, not extended;
see `docs/theory.md` §5).

## What each hook does

| Hook | Trigger | Action |
|---|---|---|
| `SessionStart` | startup / resume / clear / **compact** | injects the normative digest (< 50 lines) via `additionalContext`. The `compact` source is how commitments survive compaction (ADR-0002). |
| `PreToolUse` | `Edit\|Write` only | **blocking Tier-0 gate** (opt-in, ADR-0007): denies the *first* edit conflicting with a pinned commitment and tells the agent how to proceed — surface & ask if the change wasn't ordered by you, state the entitlement & retry if it was (the retry passes). Enable with `tier0_gate: block` in `.scorekeeper/config.yaml` or `SCOREKEEPER_TIER0_GATE=block`. Off by default; built for weaker models that ignore advisory warnings. |
| `PostToolUse` | `Edit\|Write` only | instant Tier-0 content scan (~ms, no LLM): warns when the edit mentions a rival of a pinned `attr:` value (e.g. `pymongo` while `persistence.primary_db=postgresql`). |
| `Stop` | end of each agent turn | reads the turn from `transcript_path`, extracts commitments (1 isolated LLM call), applies operators (SUPERSEDE vs BRANCH-CONFLICT by entitlement). Async by default — a detached worker, ~0 ms added latency (ADR-0006). |
| `UserPromptSubmit` | start of each turn | drains findings produced by the async worker into `additionalContext`, so a conflict/challenge surfaces on the next turn. |
| `PreCompact` | before compaction | audit backup of `scoreboard.md` (no blocking, no injection). |

## Install

Paste into a Claude Code session — nothing to pre-install:

```
/plugin marketplace add michalstrnadel/scorekeeper
/plugin install scorekeeper@scorekeeper
```

The dispatcher (`hooks/run.sh`) resolves the scorer automatically, in order:
an installed `scorekeeper` on PATH → the in-repo `core/` via uv (dev) →
`uvx`/`pipx` fetching it from PyPI on first run (so a marketplace install needs
no manual `pip install`). It also augments PATH with the usual install dirs,
since hooks run in a non-interactive shell.

Dev, from a clone:

```bash
claude --plugin-dir ./claude-code-plugin
```

## Model backend (extraction)

The Stop-hook extraction needs a model backend (ADR-0003), auto-detected in order.
With Claude Code you already have the last one, so **no setup is required**:

```bash
export SCOREKEEPER_MODEL_URL=http://localhost:11434/v1   # local OSS (Ollama/LM Studio/vLLM)
# or  export ANTHROPIC_API_KEY=sk-ant-...                # Haiku-class API calls
# or  nothing — falls back to headless `claude -p`
```

## Storage

Everything lands in `<project>/.scorekeeper/`: `commitments/*.yaml`,
`scoreboard.md` (generated), `log.jsonl` (audit trail), `backups/`. All
human-readable, all git-committable.
