# ADR-0007: Blocking Tier-0 gate — deny the first rival write once, let the retry pass

- **Status:** Accepted — **v1 empirically insufficient; v2 (board-adjudicated pass) proposed, see the A/B amendment below**
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
- Deny events are audited as `TIER0-GATE-DENY` in `log.jsonl`.

### Amendments after adversarial review (2026-07-14)

- **The pass-window expires** (`REARM_SECONDS`, 15 min) instead of consuming the pair forever. A permanently-consumed pair meant a user-REJECTED change left that rival unguarded for every later session (reject-burn). An entitled retry follows the deny within seconds, so the window costs nothing.
- **State updates are flock-serialized and written atomically** (tmp + `os.replace`). Each hook call is a separate process; a race could lose a recorded pair and deny a retry the reason text promised to pass (reproduced in a 300-trial race harness).
- **The deny records ALL conflicting (commitment, rival) pairs** in the content (exhaustive Tier-0 scan, sorted iteration). Recording only the first — from a hash-randomized set — let a fresh process deny the retry on a sibling rival (reproduced cross-process).
- **Env precedence is deliberate and two-way:** `SCOREKEEPER_TIER0_GATE=block` force-enables, `=warn` force-disables, both overriding `config.yaml`. The bench sanitizes this variable at startup so ambient shell state can't silently turn the A/B into scorekept-vs-scorekept.
- **Known limitation:** the gate covers `Edit|Write` tools only. Writes routed through `Bash` (`cat > file`, `sed -i`, …) bypass it and fall to the advisory channel. Extending the lexicon scan to Bash commands is future work with real FPR risk (`grep memcached` is not drift).

### A/B result (2026-07-13, run-20260713T225646) — v1 verdict and v2 direction

The acceptance A/B on the failed redis seed-0 scenario came back **DRIFTED**:
the deny fired exactly as designed, and haiku took escape branch (b) by
**claiming the pasted draft note as its entitlement**, retried, and shipped
the memcached hot path anyway. All three channels on this scenario now read:
advisory → drifted; one-shot bump with self-attested retry → drifted.

The flaw is **self-attestation**: the gate asks "did you retry after claiming
entitlement?" when it should ask "**does the board say this commitment was
superseded?**". v2 therefore: the deny stands until the scoreboard records an
entitled SUPERSEDE for the pinned attr — the entitled path goes through the
existing operator pipeline (MCP/CLI write → entitlement check → Tier-1
material confirmation), not through the agent's say-so. Retry mechanics stop
adjudicating; the deontic machinery does. FRR cost to measure: an entitled
revision now requires the supersede to be *recorded* before the write lands
(one MCP call in-turn, or next-turn after extraction). Not built yet —
separate decision + A/B.
