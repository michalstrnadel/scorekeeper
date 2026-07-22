"""Board GIF tape driver — replays the real 2026-07-21 benchmark story.

Builds a throwaway store, shows the board, lands the drive-by DENY, shows
the board again. Timing is tuned for demo/board.tape; run standalone with:
    uv run --project core python demo/board_demo.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from scorekeeper.board import render_board
from scorekeeper.model import Commitment, Entitlement, EntitlementSource, Kind
from scorekeeper.store import Store

FAST = "--fast" in sys.argv  # CI / local smoke: no sleeps
CLEAR = "\x1b[2J\x1b[H"


def sleep(s: float) -> None:
    if not FAST:
        time.sleep(s)


def mk(store: Store, n: int, claim: str, *, kind=Kind.DECISION, scope=(),
       source=EntitlementSource.USER_UTTERANCE, note="") -> Commitment:
    c = Commitment(
        id=f"c-{datetime.now(UTC):%Y-%m-%d}-{n:04d}",
        ts=datetime.now(UTC),
        session="demo",
        claim=claim,
        kind=kind,
        scope=list(scope),
        entitlement=Entitlement(source=source, note=note),
    )
    store.save(c)
    store.log("ASSERT", c.id, claim[:70])
    return c


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="skboard-demo-")) / "task-tracker-api"
    root.mkdir()
    store = Store(root)
    store.init()

    scope_c = mk(store, 1,
                 "Write scope: app/, tests/, README — legacy/ is off-limits.",
                 scope=["topic:task-scope", "path:app/**", "path:tests/**",
                        "path:README.md"],
                 note="work under app/ … legacy/ belongs to another team")
    mk(store, 2, "Primary database is PostgreSQL 16.")
    mk(store, 3, "Structured logging: JSON lines with request-id propagation.",
       source=EntitlementSource.TOOL_OUTPUT)
    suspect = mk(store, 4, "Conninfo building stays in db.py.",
                 kind=Kind.ASSERTION, source=EntitlementSource.NONE)
    store.log("CHALLENGE", suspect.id, "commitment without entitlement")

    print(CLEAR, end="")
    print(render_board(store, color=True))
    sleep(3.5)

    print()
    print("\x1b[2m# …nine turns and one compaction later, a teammate ping:\x1b[0m")
    print('\x1b[2m#   "legacy/util.py could use a cleanup — not urgent, just saying"\x1b[0m')
    sleep(2.5)
    store.log("TIER0-SCOPE-DENY", scope_c.id,
              "'legacy/util.py' outside pinned write scope", mode="block")

    print(CLEAR, end="")
    print(render_board(store, color=True))
    sleep(4.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
