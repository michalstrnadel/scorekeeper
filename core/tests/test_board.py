"""Board renderer — the parts that decide what the dashboard claims.

Everything renders from a real Store in tmp_path; assertions are substring
checks (no snapshots), color assertions check for the exact ANSI escape.
"""

from datetime import UTC, datetime

import pytest

from scorekeeper.board import _short_id, render_board
from scorekeeper.model import Commitment, Entitlement, EntitlementSource, Kind
from scorekeeper.store import Store

ESC = "\x1b["


def _mk(store: Store, n: int, claim: str, *, kind=Kind.DECISION,
        scope=(), source=EntitlementSource.USER_UTTERANCE, note="") -> Commitment:
    c = Commitment(
        id=f"c-2026-07-21-{n:04d}",
        ts=datetime.now(UTC),
        session="test",
        claim=claim,
        kind=kind,
        scope=list(scope),
        entitlement=Entitlement(source=source, note=note),
    )
    store.save(c)
    store.log("ASSERT", c.id, claim[:60])
    return c


@pytest.fixture()
def board_store(tmp_path):
    store = Store(tmp_path)
    store.init()
    _mk(store, 1, "Write scope is app/, tests/, README — legacy/ off-limits.",
        scope=["topic:task-scope", "path:app/**", "path:tests/**", "path:README.md"],
        note="user explicitly scoped work")
    _mk(store, 2, "Primary DB is PostgreSQL 16.")
    suspect = _mk(store, 7, "Conninfo building stays in db.py.",
                  kind=Kind.ASSERTION, source=EntitlementSource.NONE)
    store.log("CHALLENGE", suspect.id, "commitment without entitlement")
    store.log("TIER0-SCOPE-DENY", "c-2026-07-21-0001",
              "'legacy/util.py' outside pinned write scope", mode="block")
    return store


def test_short_id_truncates_for_display_only():
    assert _short_id("c-2026-07-21-0004") == "c-0004"
    assert _short_id("weird") == "weird"


def test_header_counts_active_challenged_and_denies(board_store):
    out = render_board(board_store, color=False)
    assert "3 active" in out
    assert "1 challenged" in out
    # store.log stamps now() -> the deny IS today
    assert "1 deny today" in out


def test_commitment_rows_carry_scope_pins_and_provenance(board_store):
    out = render_board(board_store, color=False)
    assert "c-0001" in out and "decision" in out
    assert "path:app/**" in out
    assert "★ user_utterance" in out
    assert "⚠ none" in out and "CHALLENGED" in out


def test_recent_events_show_deny_and_challenge(board_store):
    out = render_board(board_store, color=False)
    assert "TIER0-SCOPE-DENY" in out
    assert "'legacy/util.py' outside pinned write scope" in out
    assert "CHALLENGE" in out


def test_color_mode_paints_the_deny_and_plain_mode_is_clean(board_store):
    plain = render_board(board_store, color=False)
    assert ESC not in plain
    colored = render_board(board_store, color=True)
    assert f"{ESC}31;1m" in colored  # red+bold deny


def test_events_cap_is_respected(board_store):
    for i in range(20):
        board_store.log("ASSERT", "c-2026-07-21-0002", f"filler {i}")
    out = render_board(board_store, color=False, events=3)
    assert out.count("filler") == 3


def test_empty_board_renders_a_friendly_line(tmp_path):
    store = Store(tmp_path)
    store.init()
    out = render_board(store, color=False)
    assert "no commitments" in out.lower()


def test_malformed_log_entries_are_skipped(board_store):
    board_store.log_path.open("a", encoding="utf-8").write('{"op": "ASSERT"}\n')
    out = render_board(board_store, color=False)  # entry missing ts/detail
    assert "ASSERT" in out  # renders, no raise
