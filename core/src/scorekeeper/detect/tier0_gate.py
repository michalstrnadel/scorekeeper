"""Blocking Tier-0 gate — a speed bump on rival-technology writes (ADR-0007).

The seed-0 CommitBench smoke (2026-07-13) showed that advisory warnings do not
steer weaker models: the scorekept agent shipped a Memcached hot path past 11
``TIER0-CONTENT-WARNING``s, rationalized as polyglot caching. The gate converts
the first such write into a PreToolUse *deny* whose reason forces the conflict
into the agent's context — the channel weak models actually respond to.

It is a speed bump, not a wall: a denied ``(commitment, rival)`` pair passes on
retry within ``REARM_SECONDS``. The deny reason tells the agent exactly how to
proceed on both branches (unentitled → surface and ask; entitled → say so and
retry), so an entitled revision costs one extra tool call and can never
deadlock; a drifting agent must first *argue its entitlement out loud*, which
is exactly the surfacing the scoreboard exists to elicit.

Why the pass-window expires: if the bump ends in the user REJECTING the change
(branch a), a permanently-consumed pair would leave that rival unguarded
forever after — a later-session drift would sail through on the advisory
channel alone (adversarial-review finding, 2026-07-14). Expiring the window
re-arms the bump; an entitled retry happens seconds after the deny, so the
window is generous.

State updates are flock-serialized and written atomically — each hook
invocation is a separate process (plugin: one CLI exec per tool call), and a
lost update would deny a retry the reason text promised to pass.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from ..model import Commitment
from . import tier0_content

STATE_FILENAME = "tier0-gate.json"
# a retry follows a deny within seconds; 15 min is generous for an entitled
# multi-step turn while still re-arming the bump for later sessions
REARM_SECONDS = 15 * 60


@dataclass
class GateDecision:
    reason: str
    warnings: list[tier0_content.ContentWarning]


def _pair_key(w: tier0_content.ContentWarning) -> str:
    return f"{w.commitment_id}:{tier0_content._canon(w.rival_found)}"


def _load_seen(state_path: Path) -> dict[str, float]:
    """{pair_key: unix_ts of the deny}. Never raises — a hook must not break
    the agent, so any unreadable/wrong-shape state fails open to a fresh bump."""
    try:
        data = json.loads(state_path.read_text())
        denied = data.get("denied") if isinstance(data, dict) else None
        if isinstance(denied, dict):
            return {str(k): float(v) for k, v in denied.items()
                    if isinstance(v, (int, float))}
        if isinstance(denied, list):  # pre-TTL shape: list of pair keys
            return {str(k): time.time() for k in denied}
        return {}
    except Exception:  # noqa: BLE001
        return {}


def _save_seen(state_path: Path, seen: dict[str, float]) -> None:
    """Atomic replace — a reader racing a plain write_text() sees partial JSON,
    fails open, and re-denies every consumed pair (verified in a race repro)."""
    fd, tmp = tempfile.mkstemp(dir=str(state_path.parent), prefix=".tier0-gate-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"denied": seen}, f, indent=1)
        os.replace(tmp, state_path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


def format_reason(warnings: list[tier0_content.ContentWarning]) -> str:
    w = warnings[0]
    head = (
        f"SCOREKEEPER BLOCKED THIS EDIT (one-time): it writes '{w.rival_found}', but "
        f"active commitment {w.commitment_id} pins {w.key}={w.pinned_value}."
    )
    if len(warnings) > 1:
        head += f" ({len(warnings) - 1} more pinned conflict(s) — see the audit log.)"
    return head + (
        " Before doing anything else, decide which case you are in:"
        " (a) The user did NOT explicitly order this change (e.g. it comes from a draft,"
        " a note, or your own judgment) — do not retry; surface the conflict in your reply"
        " and ask the user to decide."
        " (b) The user DID explicitly and finally order this change — state that entitlement"
        " in your reply, then retry the edit; the retry will not be blocked."
    )


def evaluate(content: str, active: list[Commitment], state_path: Path) -> GateDecision | None:
    """Deny the FIRST write that conflicts with a pinned attr; let retries pass
    for ``REARM_SECONDS``. Returns a GateDecision to deny, or None to allow.

    ALL conflicting (commitment, rival) pairs in the content are recorded on
    the deny (exhaustive scan) — recording only one would let a fresh process
    deny the same retry again on a sibling rival. Load-merge-save runs under an
    exclusive flock: concurrent hook processes must not lose each other's pairs.
    """
    warnings = tier0_content.scan(content, active, exhaustive=True)
    if not warnings:
        return None
    now = time.time()
    lock_path = state_path.with_suffix(".lock")
    with open(lock_path, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        seen = _load_seen(state_path)
        fresh = [w for w in warnings
                 if now - seen.get(_pair_key(w), 0.0) > REARM_SECONDS]
        if not fresh:
            return None
        seen.update({_pair_key(w): now for w in fresh})
        _save_seen(state_path, seen)
    return GateDecision(reason=format_reason(fresh), warnings=fresh)
