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

*(none yet)*
