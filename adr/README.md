# Architecture Decision Records

Every non-trivial decision is recorded here as an ADR **and** mirrored as a commitment in the project scoreboard (`.scorekeeper/scoreboard.md`). This is the project dogfooding its own thesis (SPEC §4.1.6, §10.3).

Format: `NNNN-short-slug.md`. Status one of: Proposed · Accepted · Superseded · Deprecated.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-project-name.md) | Project name | Accepted |
| [0002](0002-compact-survival-via-sessionstart.md) | Compaction survival via SessionStart(source=compact), not PreCompact injection | Accepted |
| [0003](0003-pluggable-model-backends.md) | Pluggable model backends — local OSS first-class | Accepted |
| [0004](0004-extraction-trigger-design.md) | Extraction trigger: Stop 1×/turn + PostToolUse(Edit\|Write) Tier-0 | Accepted |
| [0005](0005-judge-pipeline.md) | Judge pipeline: cross-family Gemini + S8 protocol | Accepted |
