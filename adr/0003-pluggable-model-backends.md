# ADR-0003: Pluggable model backends — local open-source models are first-class

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

The extractor and the Tier-1 detector are isolated LLM calls (SPEC §4.1.4). The SPEC assumed a Haiku-class Anthropic model. Michal's requirement: the whole pipeline must be runnable on a **local open-source model** — both for cost and for open-source adoption (no vendor lock-in for an Apache-2.0 tool).

## Decision

A `ModelBackend` protocol (`backends/base.py`) with one method: `complete(system, user, schema) -> dict` (JSON-schema-constrained output). Three implementations:

1. **`openai_compat.py`** — any OpenAI-compatible endpoint. One client covers Ollama, LM Studio, and vLLM (all serve this API). This is the local-OSS path.
2. **`anthropic_api.py`** — Anthropic SDK, default model `claude-haiku-4-5-20251001`.
3. **`claude_cli.py`** — headless `claude -p` fallback (uses the user's subscription; slowest).

**Auto-detection order:** `SCOREKEEPER_MODEL_URL` set → openai_compat; else `ANTHROPIC_API_KEY` set → anthropic_api; else claude_cli. Overridable in `.scorekeeper/config.yaml`.

## Honesty clause

Extraction recall and detector FPR are **measured per-backend** and reported per-backend. Benchmark reference numbers run on Haiku; local backends are fully supported and evaluated, not promised to match. Weaker JSON compliance of small local models is mitigated by write-path validation + one retry with a repair prompt (Cognee lesson, SPEC §4.1.3).

## Consequences

- Reference local model chosen empirically in Phase 0 (candidates: Qwen3-8B, Llama-3.1-8B via Ollama).
- The backend abstraction is also what makes the eval harness's judge model swappable.
