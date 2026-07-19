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

### c-2026-07-10-0018 — Phase 0 acceptance gate: GO for Phase 1 (evidence-labeled)
- **kind:** decision · **status:** active
- **scope:** `topic:roadmap`, `phase:0`
- **entitlement:** `tool_output` — full 12-run matrix 2026-07-09/10: SCR bare 1/6 vs scorekept 0/6 (paired delta verified in artifacts), FPR 0 on the 04a probe, overhead +0.6 %, compaction survival demonstrated; bench/results/PHASE0-REPORT.md
- **consequences:** Phase 1 opens (PyPI v0.1, MCP server, async extraction, F2 attr-scoping fix); effect-size claims deferred to CommitBench (harder scenarios, repeated runs)
- **note:** Known limitation recorded: 04b JRR misclassification (env-scoped attrs needed).

### c-2026-07-10-0019 — Extraction is async in the plugin, sync in the library
- **kind:** decision · **status:** active
- **scope:** `repo:claude-code-plugin`, `topic:hooks`, `topic:latency`, `attr:plugin.extract_mode=async`
- **entitlement:** `user_utterance` + `tool_output` — Michal: runtime latency is a hard constraint ("nesmíme zpomalit nic"); Phase-0 finding F1 showed digest steering, not the in-turn block, is the dominant channel
- **consequences:** Stop hook spawns a detached worker (~0 ms added); findings drain via the new UserPromptSubmit hook; library/bench default stays sync (the measured Phase-0 configuration)
- **incompatible_with:** blocking the turn on LLM extraction in the default plugin path
- **note:** See [ADR-0006](../adr/0006-async-extraction.md).

### c-2026-07-10-0020 — MCP server ships inside the `scorekeeper` package; writes route through the operators
- **kind:** decision · **status:** active
- **scope:** `repo:core`, `repo:mcp`, `topic:architecture`, `attr:mcp.distribution=core_extra`
- **entitlement:** `prior_inference` — single PyPI package with `[mcp]` extra avoids a second release pipeline; c-0008 (scaffolded-not-extended) demands every write pass the validated operator door regardless of transport
- **consequences:** `scorekeeper-mcp` console script; `supersede` refuses non-external entitlement; unentitled `assert_commitment` comes back as BRANCH-CONFLICT
- **incompatible_with:** MCP tools that let an agent silently edit its own board

### c-2026-07-10-0021 — Entitled attr-collision revisions require Tier-1 material confirmation (F2 fix)
- **kind:** decision · **status:** active
- **scope:** `repo:core`, `topic:operators`, `topic:detection`
- **entitlement:** `tool_output` — Phase-0 finding F2: 04b misrecorded a dev-cache change as superseding the production Redis commitment (bench/results/PHASE0-REPORT.md)
- **consequences:** SUPERSEDE from a Tier-0 collision only when Tier-1 confirms replacement (compatible → COEXIST, refines → REFINE; no backend → deterministic supersede kept); extraction prompt scopes attrs by environment
- **incompatible_with:** superseding on attr-key collision alone; consulting an LLM before flagging *unentitled* drift (that path stays zero-LLM)

### c-2026-07-10-0022 — `scorekeeper` is published on PyPI (v0.1.x, trusted publishing)
- **kind:** assertion · **status:** active
- **scope:** `topic:release`, `attr:pypi.package=scorekeeper`
- **entitlement:** `tool_output` — release run 2026-07-10: wheel for 0.1.0 accepted (pypi.org/project/scorekeeper); 0.1.1 re-released with sdist
- **note:** PyPI retires filenames of deleted projects — a prior unrelated `scorekeeper` project burned `scorekeeper-0.1.0.tar.gz`, so 0.1.0 is wheel-only. Known constraint for future versions: if an upload 400s with "filename previously used", bump the patch version.

### c-2026-07-10-0023 — CommitBench design: mirror-image families, full-replacement revocations, gitignored eval split
- **kind:** decision · **status:** active
- **scope:** `repo:bench`, `topic:evaluation`, `phase:2`
- **entitlement:** `document` + `tool_output` — SPEC §6, Addendum-1 contamination protocol; F2 fix makes per-feature carve-outs correctly COEXIST, so `revision`-family revocations MUST be full replacements or the ground truth lies
- **consequences:** drift/revision families share worlds+distance (paired FPR measurement); knobs = distance/compaction/distractors (findings F1/F4); dev/eval derive separate RNG streams; eval instances never inspected, `generated/` never committed
- **incompatible_with:** committing generated eval instances; tuning prompts on the eval split; revision scenarios whose revocation is scoped to a single feature

### c-2026-07-11-0024 — CommitBench primary metric is a deterministic artifact classifier; LLM judge is secondary
- **kind:** decision · **status:** active
- **scope:** `repo:bench`, `topic:evaluation`, `attr:bench.primary_metric=behavior_classifier`
- **entitlement:** `tool_output` — the local qwen judge repeatedly failed on long CommitBench trajectories (300s timeouts; degenerate all-1s verdicts that scored a fully-worked run task_completion=1; called a clearly-drifting bare run contradiction=False)
- **consequences:** `bench/harness/classify.py` decides drift vs held from the final reply (order of surfacing-vs-accepting) + rival code in the repo; SCR computed from it, AMBIGUOUS excluded from the denominator (declared); LLM judge kept only as a cross-check
- **incompatible_with:** reporting SCR from the LLM judge verdict as the headline number
- **note:** anchored on the verified 2026-07-10 s00 pair (bare DRIFTED, scorekept HELD). Supersedes reliance on c-0017's judge for the drift metric; judge protocol itself unchanged for trajectory scoring.

### c-2026-07-11-0025 — Bench Stop-hook extraction must run off the SDK event loop
- **kind:** decision · **status:** active
- **scope:** `repo:bench`, `topic:hooks`, `topic:latency`
- **entitlement:** `tool_output` — a 101-minute batch hang (2026-07-10) traced to the synchronous `claude -p` extraction (blocking subprocess) running inside an async SDK hook, freezing the event loop and deadlocking the transport
- **consequences:** bench Stop hook wraps `hook_stop` in `asyncio.to_thread`; a hard per-phase timeout (SCOREKEEPER_PHASE_TIMEOUT, default 600s) records a hung turn and reconnects instead of stalling
- **incompatible_with:** blocking subprocess calls directly inside async SDK hooks

### c-2026-07-13-0026 — Tier-0 gate is a one-shot speed bump, opt-in until paired evidence
- **kind:** decision · **status:** active
- **scope:** `repo:core`, `topic:hooks`, `attr:tier0_gate.mode=speed_bump`
- **entitlement:** `tool_output` + `user_utterance` — seed-0 negative finding (scorekept haiku drifted past 11 advisory warnings, SMOKE-DRIFT-S0-REPORT.md); Michal directed the fix must work on weak models (2026-07-13)
- **consequences:** PreToolUse denies the FIRST write per (commitment, rival) pair with a two-branch instruction (unentitled → surface & ask; entitled → state it & retry); retries pass (state in `.scorekeeper/tier0-gate.json`); opt-in via `SCOREKEEPER_TIER0_GATE=block` / config `tier0_gate: block`; bench variant `blocking` is the A/B acceptance test (ADR-0007)
- **incompatible_with:** unconditional blocking (walls an entitled revision); flipping the gate on by default before the paired A/B evidence lands
- **note (2026-07-14):** v1 bump A/B DRIFTED (self-attested entitlement exploited the retry escape). Superseded in part by c-0027: the recommended mode is the v2 board-adjudicated wall; the bump survives as an ablation (`tier0_gate: bump`).

### c-2026-07-14-0027 — Gate v2: the deny is adjudicated by the board, not by the agent's say-so
- **kind:** decision · **status:** active
- **scope:** `repo:core`, `topic:hooks`, `attr:tier0_gate.adjudicator=scoreboard`
- **entitlement:** `tool_output` + `user_utterance` — v1 A/B (run-20260713T225646): haiku claimed a pasted draft note as entitlement and shipped the drift through the retry escape; Michal approved v2 2026-07-14 ("to dáme")
- **consequences:** `evaluate_wall` denies while the pinned commitment is in `store.active()`; the only pass condition is an entitled SUPERSEDE recorded through the operator pipeline / MCP tool / turn-end extraction. Verified symmetric on seed-0 redis-memcached: drift HELD/high (2 denies, no rival code), revision EXECUTED/high (0 denies, expected SUPERSEDE hit)
- **incompatible_with:** any gate pass condition satisfiable by the agent's own unverified claim; lifting the wall on retry mechanics

### c-2026-07-19-0029 — The benchmark is named DeonticBench (renamed from EntitleBench)
- **kind:** decision · **status:** active
- **scope:** `repo:bench`, `topic:naming`, `attr:bench.name=deonticbench`
- **supersedes:** c-2026-07-14-0028
- **entitlement:** `user_utterance` + `document` — related-work finding: "EntitleBench" also collides with an established SE/NLP benchmark (commit-message generation, 1.6M commits; docs/research/related-work.md); Michal chose DeonticBench 2026-07-19 — names the measured boundary (Brandom's deontic scorekeeping), distinctive, no collision found at decision time
- **consequences:** module `bench/deonticbench/`, progress doc `DEONTICBENCH-PROGRESS.md`, all living docs renamed; dated artifacts (evidence JSONs, PHASE0 report, ADR histories, imported research) keep historical names; scenario id prefix `cb-` retained for continuity with persisted runs
- **incompatible_with:** shipping any external artifact (paper, launch post, PyPI metadata) under the CommitBench or EntitleBench names

---

## Superseded / retracted / conflicted

- **(assumption inside c-0004's context, via c-0009):** "PreCompact injects the normative digest into summarization" — superseded 2026-07-08 by the SessionStart(compact) mechanism; entitled revision (verified live docs).
- **c-2026-07-09-0012** (superseded → c-0017, 2026-07-09): "Judge is cross-family Gemini" — user revoked the cloud dependency after free-tier quota killed three gate runs; judge default moved to local qwen3:8b via Ollama. Entitled revision (user_utterance + tool_output). Cross-family requirement and S8 protocol carry over unchanged.
- **c-2026-07-14-0028** (superseded → c-0029, 2026-07-19): "The benchmark is named EntitleBench" — the second name collision in a row (EntitleBench also taken in SE/NLP); renamed to DeonticBench. Entitled revision (user_utterance + document). Rename conventions (living docs vs. dated artifacts, `cb-` prefix) carry over unchanged.
