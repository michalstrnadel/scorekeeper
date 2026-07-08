# scorekeeper-core

Harness-agnostic core: the commitment data model, storage (Markdown + YAML records + SQLite index), and the operator API (`ASSERT`, `SUPPORT`, `REFINE`, `SUPERSEDE`, `BRANCH-CONFLICT`, `CHALLENGE`, `RETRACT`). No dependency on any specific harness.

Python for v0.1 (SPEC §4.5). Not implemented yet — Phase 0/1.

See [`../docs/SPEC-cs.md`](../docs/SPEC-cs.md) §4 for the data model and operators.
