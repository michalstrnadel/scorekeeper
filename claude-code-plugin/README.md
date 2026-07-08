# scorekeeper — Claude Code plugin

Primary integration (SPEC §4.5). Deterministic hooks drive the scoreboard —
extraction is never left to the agent's discretion (scaffolded, not extended;
see `docs/theory.md` §5).

## What each hook does

| Hook | Trigger | Action |
|---|---|---|
| `SessionStart` | startup / resume / clear / **compact** | injects the normative digest (< 50 lines) via `additionalContext`. The `compact` source is how commitments survive compaction (ADR-0002). |
| `PostToolUse` | `Edit\|Write` only | instant Tier-0 content scan (~ms, no LLM): warns when the edit mentions a rival of a pinned `attr:` value (e.g. `pymongo` while `persistence.primary_db=postgresql`). |
| `Stop` | end of each agent turn | reads the turn from `transcript_path`, extracts commitments (1 isolated LLM call), applies operators (SUPERSEDE vs BRANCH-CONFLICT by entitlement), and blocks with a conflict/challenge report when findings exist (ADR-0004). |
| `PreCompact` | before compaction | audit backup of `scoreboard.md` (no blocking, no injection). |

## Setup

The hooks need a model backend for the Stop-hook extraction (ADR-0003), in
auto-detect order:

```bash
export SCOREKEEPER_MODEL_URL=http://localhost:11434/v1   # local OSS (Ollama/LM Studio/vLLM)
# or
export ANTHROPIC_API_KEY=sk-ant-...                       # Haiku-class API calls
# or nothing — falls back to headless `claude -p` (slowest)
```

## Try it (dev, from this repo)

```bash
claude --plugin-dir ./claude-code-plugin
```

The dispatcher (`hooks/run.sh`) resolves the CLI automatically: an installed
`scorekeeper` package on PATH, or the in-repo `core/` via uv.

## Install (once published)

```bash
claude plugin install https://github.com/michalstrnadel/scorekeeper
```

## Storage

Everything lands in `<project>/.scorekeeper/`: `commitments/*.yaml`,
`scoreboard.md` (generated), `log.jsonl` (audit trail), `backups/`. All
human-readable, all git-committable.
