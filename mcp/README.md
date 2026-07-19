# scorekeeper-mcp

MCP server exposing the scoreboard to any harness (LangGraph, Letta, …). Implemented in the core package — `core/src/scorekeeper/mcp_server.py`:

```bash
pip install "scorekeeper[mcp]"
SCOREKEEPER_ROOT=/path/to/project scorekeeper-mcp   # stdio transport
```

Tools: `get_scoreboard`, `get_digest`, `assert_commitment`, `check_compatibility` (dry-run), `supersede`, `challenge`, `retract` (SPEC §4.5).

Design constraint (c-0008, theory.md §5): this server is for **harness-level** integration — `assert_commitment` routes through the validated operator pipeline (Tier-0/Tier-1, the SUPERSEDE vs BRANCH-CONFLICT entitlement gate), so an agent given these tools still cannot silently rewrite its own board: an unentitled replacement comes back as a BRANCH-CONFLICT. `supersede` and `retract` are explicit, targeted status transitions — they skip the pipeline by design but stay entitlement-gated (`supersede` refuses non-external entitlement outright).

LangGraph integration as a graph node (Hindsight pattern): planned, Phase 3 (see [ROADMAP](../ROADMAP.md)).
