"""Terminal dashboard for the scoreboard — `scorekeeper board`.

Pure renderer: Store in, string out. No tty inspection here (the CLI decides
`color`), no new dependencies — plain ANSI 16-color escapes so it degrades
gracefully anywhere. Design: docs/superpowers/specs/2026-07-22-board-tui-design.md.
"""

from __future__ import annotations

import textwrap
from datetime import datetime

from .model import EXTERNAL_SOURCES, Status
from .store import Store

_CODES = {
    "green": "32", "yellow": "33", "red": "31", "blue": "34",
    "magenta": "35", "cyan": "36", "dim": "2", "bold": "1",
}


def _c(text: str, *styles: str, on: bool = True) -> str:
    if not on or not styles:
        return text
    seq = ";".join(_CODES[s] for s in styles)
    return f"\x1b[{seq}m{text}\x1b[0m"


def _short_id(cid: str) -> str:
    """Display-only truncation: c-2026-07-21-0004 -> c-0004."""
    parts = cid.split("-")
    return f"c-{parts[-1]}" if len(parts) > 1 else cid


def _op_styles(op: str) -> tuple[str, ...]:
    if op.endswith("DENY"):
        return ("red", "bold")
    if op in ("ASSERT", "SUPERSEDE", "REFINE"):
        return ("green",)
    if op == "CHALLENGE":
        return ("yellow",)
    return ("dim",)


def _hhmm(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%H:%M")
    except (ValueError, TypeError):
        return "--:--"


def _is_today(iso: str) -> bool:
    try:
        ts = datetime.fromisoformat(iso).astimezone()
    except (ValueError, TypeError):
        return False
    return ts.date() == datetime.now().astimezone().date()


def render_board(store: Store, *, color: bool = True, width: int = 80,
                 events: int = 8) -> str:
    commitments = store.all()
    entries = store.log_entries()
    active = [c for c in commitments if c.status is Status.ACTIVE]
    conflicted = [c for c in commitments if c.status is Status.CONFLICTED]
    challenged_ids = {e.get("commitment_id") for e in entries
                      if e.get("op") == "CHALLENGE"}
    challenged = [c for c in active if c.id in challenged_ids]
    denies_today = sum(
        1 for e in entries
        if str(e.get("op", "")).endswith("DENY") and _is_today(str(e.get("ts", "")))
    )

    bar = _c("─" * width, "dim", on=color)
    lines: list[str] = []

    # header
    head = [_c("◆ scorekeeper", "magenta", "bold", on=color),
            _c("·", "dim", on=color), store.root.resolve().name,
            _c("·", "dim", on=color),
            _c(f"{len(active)} active", "green", on=color)]
    if challenged:
        head += [_c("·", "dim", on=color),
                 _c(f"{len(challenged)} challenged", "yellow", on=color)]
    if conflicted:
        head += [_c("·", "dim", on=color),
                 _c(f"{len(conflicted)} conflicted", "red", on=color)]
    if denies_today:
        head += [_c("·", "dim", on=color),
                 _c(f"{denies_today} deny today" if denies_today == 1
                    else f"{denies_today} denies today", "red", on=color)]
    lines.append(" ".join(head))
    lines.append(bar)

    # active commitments
    lines.append(_c(" ACTIVE COMMITMENTS", "bold", on=color))
    if not active:
        lines.append(_c("  (no commitments recorded yet — the board is empty)",
                        "dim", on=color))
    for c in active:
        claim = textwrap.shorten(c.claim, width=width - 20, placeholder="…")
        kind_txt = f"{c.kind.value:<9}"
        lines.append(f" {_c(_short_id(c.id), 'magenta', on=color)} "
                     f"{_c(kind_txt, 'cyan', on=color)} {claim}")
        pins = [s for s in c.scope if s.startswith(("path:", "topic:"))]
        if pins:
            lines.append(f"        {_c('scope', 'dim', on=color)} "
                         f"{_c('  '.join(pins), 'blue', on=color)}")
        src = c.entitlement.source.value
        if c.entitlement.source in EXTERNAL_SOURCES:
            glyph = _c(f"★ {src}", "green", on=color)
        else:
            marker = " — CHALLENGED" if c.id in challenged_ids else ""
            glyph = _c(f"⚠ {src}{marker}", "yellow", on=color)
        note = ""
        if c.entitlement.note:
            quoted = textwrap.shorten(c.entitlement.note, width=width - 30,
                                      placeholder="…")
            note = " " + _c(f'"{quoted}"', "dim", on=color)
        lines.append(f"        {_c('from ', 'dim', on=color)} {glyph}{note}")

    # recent events
    lines.append(bar)
    lines.append(_c(" RECENT EVENTS", "bold", on=color))
    recent = [e for e in entries if e.get("op")][-events:]
    for e in reversed(recent):
        op = str(e.get("op", ""))
        detail = textwrap.shorten(str(e.get("detail", "")), width=width - 30,
                                  placeholder="…")
        op_txt = f"{op:<10}"
        cid_txt = _c(_short_id(str(e.get("commitment_id", ""))), "magenta", on=color)
        lines.append(f" {_c(_hhmm(str(e.get('ts', ''))), 'dim', on=color)} "
                     f"{_c(op_txt, *_op_styles(op), on=color)} "
                     f"{cid_txt}  {detail}")
    if not recent:
        lines.append(_c("  (no events yet)", "dim", on=color))

    return "\n".join(lines)
