# Project scoreboard

> `scorekeeper` dogfoods itself (SPEC §4.1.6). Until the tool exists, this scoreboard is maintained **by hand**; once the MVP works, it is generated. Each non-trivial project decision is recorded here as a commitment **and** as an ADR.

Legend — kind: `decision | assertion | promise | assumption`. status: `active | refined | superseded | conflicted | retracted`. entitlement.source: `user_utterance | tool_output | document | prior_inference | none`.

---

## Active commitments

### c-2026-07-08-0001 — License is Apache-2.0
- **kind:** decision · **status:** active
- **scope:** `repo:root`, `topic:licensing`
- **entitlement:** `document` — SPEC §7 (Phase 1), §10.1
- **incompatible_with:** any GPL/copyleft relicensing

### c-2026-07-08-0002 — Project artifacts (code, docs, paper) are in English
- **kind:** decision · **status:** active
- **scope:** `repo:root`, `topic:language`
- **entitlement:** `document` — SPEC §5 preamble, §10.1
- **note:** The Czech spec (`docs/SPEC-cs.md`) is the exception, kept as the source-of-record vision.

### c-2026-07-08-0003 — `core` language for v0.1 is Python
- **kind:** decision · **status:** active
- **scope:** `repo:core`, `topic:stack`
- **entitlement:** `document` — SPEC §4.5, §10; TS port explicitly deferred
- **incompatible_with:** shipping v0.1 core in a non-Python runtime

### c-2026-07-08-0004 — Primary integration is Claude Code hooks; overlay, not runtime
- **kind:** decision · **status:** active
- **scope:** `repo:claude-code-plugin`, `topic:architecture`
- **entitlement:** `document` — SPEC §4.1.1, §4.5

### c-2026-07-08-0005 — Storage is transparent: Markdown + YAML records + SQLite index, git-committable
- **kind:** decision · **status:** active
- **scope:** `topic:storage`
- **entitlement:** `document` — SPEC §4.1.5, §4.6
- **incompatible_with:** an opaque/binary-only store

### c-2026-07-08-0006 — Phase 0 scope is decisions in coding tasks only
- **kind:** decision · **status:** active
- **scope:** `topic:scope`, `phase:0`
- **entitlement:** `document` — SPEC §7 Phase 0, §8 (scope creep is the main risk)
- **incompatible_with:** universal "extract all commitments" in Phase 0

### c-2026-07-08-0007 — Project name is `scorekeeper`, tagline "commitment tracking for LLM agents"
- **kind:** decision · **status:** active
- **scope:** `repo:root`, `topic:naming`
- **entitlement:** `user_utterance` + `tool_output` — Michal locked `scorekeeper`; availability verified 2026-07-08 (PyPI + `michalstrnadel/scorekeeper` repo free)
- **supersedes:** the earlier `assumption` that the name was open
- **note:** See [ADR-0001](../adr/0001-project-name.md) (Accepted). Distribution fallback `agent-scorekeeper` kept only if a collision surfaces.

### c-2026-07-08-0008 — Architecture is scaffolded, not extended (external scorer outside agent authority)
- **kind:** decision · **status:** active
- **scope:** `topic:architecture`, `topic:stance`
- **entitlement:** `prior_inference` + `document` — Sterelny scaffolded mind + Brandom social scorekeeping converge on the same choice already justified by Mercier & Sperber / Letta lesson (SPEC §2.4, §4.1.2); see [theory.md §5](../docs/theory.md)
- **consequences:** the scoreboard MUST be maintained by deterministic hooks + isolated scorer, never by the agent's self-editing
- **incompatible_with:** an extended-mind / self-editing-memory design where the agent owns and edits its own scoreboard at runtime (c-0004 reinforces this)

### c-2026-07-08-0009 — Compaction survival runs through SessionStart(source=compact) digest injection
- **kind:** decision · **status:** active
- **scope:** `repo:claude-code-plugin`, `topic:architecture`, `topic:hooks`
- **entitlement:** `tool_output` — live Claude Code docs verified 2026-07-08: PreCompact cannot inject into the summary; SessionStart supports `additionalContext` and fires with `source:"compact"`
- **supersedes:** the SPEC §4.5 assumption that PreCompact injects the digest into summarization (justified revision — new evidence)
- **note:** PreCompact retained for audit backup only. See [ADR-0002](../adr/0002-compact-survival-via-sessionstart.md).

### c-2026-07-08-0010 — Model backends are pluggable; local open-source models are first-class
- **kind:** decision · **status:** active
- **scope:** `repo:core`, `topic:backends`
- **entitlement:** `user_utterance` — Michal: the pipeline must not require Haiku; local OSS model support required
- **consequences:** ModelBackend protocol with openai_compat (Ollama/LM Studio/vLLM) + anthropic_api + claude_cli; auto-detect SCOREKEEPER_MODEL_URL → ANTHROPIC_API_KEY → claude -p; quality measured per-backend
- **incompatible_with:** hard dependency on any single model vendor in core
- **note:** See [ADR-0003](../adr/0003-pluggable-model-backends.md).

### c-2026-07-08-0011 — Extraction triggers: Stop hook 1×/turn; PostToolUse(Edit|Write) Tier-0 only
- **kind:** decision · **status:** active
- **scope:** `repo:claude-code-plugin`, `topic:hooks`, `topic:cost`
- **entitlement:** `user_utterance` — Michal selected this trade-off in planning (2026-07-08)
- **incompatible_with:** LLM extraction after every tool use
- **note:** See [ADR-0004](../adr/0004-extraction-trigger-design.md).

### c-2026-07-09-0017 — Judge default is LOCAL open-source (qwen3:4b via Ollama), S8 protocol unchanged
- **kind:** decision · **status:** active (refined 2026-07-09: 8b → 4b)
- **scope:** `repo:bench`, `topic:evaluation`, `attr:bench.judge_family=qwen_local`
- **entitlement:** `user_utterance` + `tool_output` — Michal revoked the Gemini dependency and requested a single model; qwen3:8b failed 4 pull attempts (persistent CDN EOF), qwen3:4b pulled cleanly; A.1 explicitly endorses mid-size + strong protocol over raw model size
- **supersedes:** c-2026-07-09-0012
- **incompatible_with:** any Claude-family model scoring Claude-agent runs; hard dependency on a cloud judge
- **note:** Protocol (S8, anchored rubric, median-of-3, temp 0) unchanged; Gemini stays as optional second family via env. See [ADR-0005](../adr/0005-judge-pipeline.md) Revision.

### c-2026-07-09-0013 — Statistics: Wilson CIs (binary), smooth bootstrap (continuous), clustered SE, paired design
- **kind:** decision · **status:** active
- **scope:** `repo:bench`, `topic:evaluation`, `topic:statistics`
- **entitlement:** `document` — Addendum-1 §A.2
- **incompatible_with:** CLT-based intervals on small-N binary metrics; unclustered SE across scenarios sharing an environment

### c-2026-07-09-0014 — Meta-eval gate: CV ≤ 0.05 on the measurement instrument (judge) before any full matrix
- **kind:** decision · **status:** active (refined 2026-07-09)
- **scope:** `repo:bench`, `topic:evaluation`
- **entitlement:** `document` + `tool_output` — Addendum-1 §A.3; refinement grounded in the first gate run (judge CV 0.056, extractor CV 0.29): instrument vs. treatment distinction, Q10
- **consequences:** the full acceptance matrix MUST NOT run before this gate passes; judge stabilized via per-criterion median-of-3; extractor variance is treatment behavior → A.2 Wilson CIs, reported as diagnostic

### c-2026-07-09-0015 — Interop: map onto xAIF + PROV-O, no home-grown ontology; Commitment Stores cited as prior art
- **kind:** decision · **status:** active
- **scope:** `repo:docs`, `topic:interop`, `topic:paper`
- **entitlement:** `document` — Addendum-1 §B.1, §B.4 (research 04)
- **note:** docs/interop.md + theory.md §6 (Hamblin/Mackenzie/DGDL-DGEP).

### c-2026-07-09-0016 — ZMENY_ITERACE_1.md was never delivered; Addendum-1 applies standalone
- **kind:** assumption · **status:** active
- **scope:** `repo:docs`, `topic:spec`
- **entitlement:** `tool_output` — file search across Downloads and repo found no such document (2026-07-09)
- **note:** QUESTIONS Q7; reconcile if the document surfaces.

---

## Superseded / retracted / conflicted

- **(assumption inside c-0004's context, via c-0009):** "PreCompact injects the normative digest into summarization" — superseded 2026-07-08 by the SessionStart(compact) mechanism; entitled revision (verified live docs).
- **c-2026-07-09-0012** (superseded → c-0017, 2026-07-09): "Judge is cross-family Gemini" — user revoked the cloud dependency after free-tier quota killed three gate runs; judge default moved to local qwen3:8b via Ollama. Entitled revision (user_utterance + tool_output). Cross-family requirement and S8 protocol carry over unchanged.
