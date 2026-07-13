# ADR-0007: Blocking Tier-0 gate — deny the first rival write once, let the retry pass

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

The seed-0 CommitBench smoke (`bench/results/SMOKE-DRIFT-S0-REPORT.md`) produced a verified negative finding: on the redis-memcached pair the scorekept agent (claude-haiku-4-5) drifted *additively* — it built the tempted hot path on Memcached with a polyglot rationalization — while the overlay mechanically worked: 11 `TIER0-CONTENT-WARNING`s fired and the Stop-hook extractor even recorded the drift onto the board. **Advisory context is not a sufficient steering channel for weaker models.** Making weak models hold commitments is a core value proposition, so the overlay needs a channel that interrupts the action itself, not just annotates it.

## Decision

A **PreToolUse gate** (`detect/tier0_gate.py`, hook `pre-tool-use`) that runs the same Tier-0 rival scan *before* a Write/Edit lands:

- **Speed bump, not a wall.** The first write conflicting with a pinned attr is denied (`permissionDecision: deny`). The deny reason names the commitment and spells out both branches: (a) not explicitly ordered by the user → don't retry, surface the conflict and ask; (b) explicitly ordered (entitled revision) → state the entitlement in the reply and retry. Each `(commitment, rival)` pair is denied **once per board** (persisted in `.scorekeeper/tier0-gate.json`), so the retry passes.
- **Why once:** an entitled revision costs exactly one extra tool call and can never deadlock (bounded FRR/latency cost); a drifting agent is forced to argue its entitlement in-context — the surfacing the scoreboard exists to elicit. Weak models follow explicit in-context instructions far better than ambient warnings.
- **Opt-in for now:** `SCOREKEEPER_TIER0_GATE=block` env or `tier0_gate: block` in `.scorekeeper/config.yaml`; advisory PostToolUse warnings remain the default channel. The plugin registers the PreToolUse hook unconditionally (no-op unless enabled). Default flip is a separate decision pending paired evidence (`--variant blocking` in the bench measures exactly this against `scorekept`).

## Consequences

- New bench variant `blocking` = full system + gate; the A/B against `scorekept` on the failed redis seed-0 scenario is the acceptance test for the channel.
- The gate shares the Tier-0 lexicon (small, high-precision, alias-folded), so its FPR inherits Tier-0's; `must_not_fire` probes in the revision family measure the entitled-path cost (agent must retry once).
- One-shot state is per-board, not per-session: after a deny, later sessions won't re-block the same pair. Conservative by design — the bump exists to force one explicit surfacing, not to nag.
- Deny events are audited as `TIER0-GATE-DENY` in `log.jsonl`.
