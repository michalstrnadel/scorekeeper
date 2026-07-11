# Contributing to scorekeeper

Thanks for looking! scorekeeper is early and the design is the artifact right now — **trying it and telling us what broke is as valuable as code.** This guide gets you from clone to a passing test suite in a couple of minutes, then points at the good places to start.

## Try it in 60 seconds

No clone needed — the core is on PyPI:

```bash
pip install scorekeeper
python -m scorekeeper --help
```

Or see the mechanism live (clone + [uv](https://docs.astral.sh/uv/)):

```bash
git clone https://github.com/michalstrnadel/scorekeeper && cd scorekeeper
uv run --project core python demo/drift_demo.py
```

You'll watch a live scoreboard reject an agent's *own* drift (BRANCH-CONFLICT) but accept a user-ordered revision of the same shape (SUPERSEDE) — the whole thesis in ~20 seconds.

## Use it on a real Claude Code session

```bash
claude --plugin-dir ./claude-code-plugin
```

Four hooks attach: the digest injects your commitments each turn (and survives context compaction), a millisecond content scan flags rival-tech edits, and turn-end extraction records new commitments. Watch `.scorekeeper/scoreboard.md` grow. **This is the path we most want feedback on** — open an issue with what it caught, what it missed, and what annoyed you.

## Dev setup

Everything lives in `core/` (the library + CLI + MCP server), driven by `uv`:

```bash
cd core
uv sync --all-extras        # deps incl. [mcp]
uv run pytest -q            # 65 tests, ~1s
uv run ruff check src tests # lint (must pass; CI enforces)
```

The benchmark harness is a separate uv project:

```bash
cd bench/harness && uv run --with pytest python -m pytest test_stats.py test_classify.py -q
cd bench/commitbench && uv run --project ../harness --with pytest python -m pytest test_generate.py -q
```

CI (`.github/workflows/ci.yml`) runs ruff + pytest on every push and PR.

## The shape of the codebase

```
core/src/scorekeeper/
  model.py       Commitment schema (the deontic vocabulary as pydantic)
  store.py       transparent storage: YAML records + log.jsonl + scoreboard.md + digest
  extract.py     turn -> commitments (isolated LLM call, narrow schema)
  detect/        tier0.py (attr collisions, no LLM) · tier1.py (material incompatibility, LLM)
                 tier0_content.py (mid-turn rival-tech scan)
  operators.py   ASSERT/SUPPORT/REFINE/SUPERSEDE/BRANCH-CONFLICT/CHALLENGE — the core distinction
  backends/      pluggable ModelBackend: openai_compat (local OSS) · anthropic_api · claude_cli
  cli.py         hook handlers (SessionStart/PostToolUse/Stop/UserPromptSubmit/PreCompact) + commands
  mcp_server.py  MCP tools over the store
```

Design rule that governs every change (see [`docs/theory.md` §5](docs/theory.md) and [ADR-0001…0006](adr/)): the scoreboard is **scaffolded, not extended** — maintained by deterministic hooks and an isolated scorer *outside the agent's authority*. The agent never edits its own board at runtime. A PR that lets it do so won't be merged; that's the thesis.

## Good places to start

- **Add a model backend** — `backends/` implements a tiny `ModelBackend` protocol (`complete(system, user) -> str`). New local runtimes (Ollama/LM Studio/vLLM already work via `openai_compat`) are welcome.
- **Add rival-tech families** — `detect/tier0_content.py` `FAMILIES` is a small high-precision lexicon (databases, caches, web frameworks…). Extend it for your stack.
- **Add a planted scenario** — `bench/tasks/` (hand-built) or a `bench/commitbench/` template family. Each is a `scenario.yaml` + `ground_truth.yaml` + seed `repo/`.
- **Port the core** — a TypeScript port is explicitly deferred (SPEC §4.5) and would be a big, welcome contribution.
- **Run it and report** — issues labeled `experience-report` (did it catch your drift? false alarms? latency?) directly shape the roadmap.

## Pull requests

- Branch, keep changes small and reviewable, add a regression test when you fix a bug.
- `uv run ruff check src tests` and `uv run pytest -q` must pass (CI enforces both).
- Conventional Commits (`feat|fix|docs|refactor|test|chore|…`); update `CHANGELOG.md` for user-visible changes.
- User-visible behavior changes should note the rationale; if it's a design decision, an ADR in `adr/` (and a line in `.scorekeeper/scoreboard.md` — we dogfood) is ideal.

## Questions

Open a [discussion or issue](https://github.com/michalstrnadel/scorekeeper/issues). For the philosophical grounding (Brandom's scorekeeping, Sterelny's scaffolded mind), start with [`docs/theory.md`](docs/theory.md).
