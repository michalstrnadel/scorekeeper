# claude-code-plugin

Primary integration (SPEC §4.5). Claude Code hooks that drive the scoreboard deterministically — extraction is not left to the agent's discretion (lesson from Letta's reliability gap, SPEC §4.1.2):

- `SessionStart` — load the active scoreboard digest (< 50 lines) into context.
- `PostToolUse` / `Stop` — extract new commitments from the last turn (isolated cheap model, narrow schema), run Tier 0+1 detection, return any conflict to the agent.
- `PreCompact` — **the key moment**: inject the normative digest into summarization so compaction preserves normative structure and drops only narrative.

> Verify the current hooks API + plugin mechanism against live docs (code.claude.com/docs) at implementation time — not against the spec (QUESTIONS Q2).

Not implemented yet — Phase 0.
