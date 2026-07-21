"""Transparent storage for the scoreboard (SPEC §4.1.5, §4.6).

Layout under ``<root>/.scorekeeper/``:
- ``commitments/<id>.yaml`` — one record per file, human-editable
- ``log.jsonl``             — append-only audit trail of every operation
- ``scoreboard.md``         — generated human-readable active state
- ``config.yaml``           — optional backend/threshold configuration

Nothing is ever deleted (Ghost Memory protection): status transitions only.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ._locking import exclusive_file_lock
from .model import Commitment, Status

DIRNAME = ".scorekeeper"
LOCK_FILENAME = "worker.lock"


def _atomic_write(path: Path, text: str) -> None:
    """tmp + os.replace — hook readers race detached workers on these files;
    a plain write_text() truncates first, and yaml.safe_load('') -> None made
    the gate silently skip its check (race reproduced, audit 2026-07-14)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


class Store:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.dir = self.root / DIRNAME
        self.commitments_dir = self.dir / "commitments"
        self.log_path = self.dir / "log.jsonl"
        self.scoreboard_path = self.dir / "scoreboard.md"
        self._write_lock_held = False

    # -- lifecycle -----------------------------------------------------------

    def init(self) -> None:
        self.commitments_dir.mkdir(parents=True, exist_ok=True)

    @property
    def exists(self) -> bool:
        return self.commitments_dir.is_dir()

    @contextlib.contextmanager
    def write_lock(self, blocking: bool = True) -> Iterator[None]:
        """Serializes every writer that allocates ids or rewrites records —
        the async worker, the sync stop hook, and the MCP write tools all
        take THIS lock (unlocked writers allocated the same commitment id,
        audit 2026-07-14). ``blocking=False`` raises BlockingIOError when
        the lock is held (used by the pending-findings drain to skip a turn
        instead of stalling a 10s hook behind a worker's LLM call).

        Re-entrant per Store instance: ``operators.apply`` locks itself so
        the one-door invariant is structural, and callers that pre-lock
        (hooks, MCP tools) nest without deadlocking. flock alone is NOT
        re-entrant across separate opens of the lock file."""
        if self._write_lock_held:
            yield
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(self.dir / LOCK_FILENAME, blocking=blocking):
            self._write_lock_held = True
            try:
                yield
            finally:
                self._write_lock_held = False

    # -- records -------------------------------------------------------------

    def save(self, c: Commitment) -> None:
        self.init()
        data = c.model_dump(mode="json")
        path = self.commitments_dir / f"{c.id}.yaml"
        _atomic_write(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    def load(self, cid: str) -> Commitment:
        path = self.commitments_dir / f"{cid}.yaml"
        return Commitment.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

    def all(self) -> list[Commitment]:
        if not self.exists:
            return []
        out = [
            Commitment.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
            for p in sorted(self.commitments_dir.glob("c-*.yaml"))
        ]
        return sorted(out, key=lambda c: c.id)

    def active(self) -> list[Commitment]:
        """Commitments that currently bind the agent (conflicted stays visible)."""
        return [c for c in self.all() if c.status in (Status.ACTIVE, Status.CONFLICTED)]

    def ids(self) -> list[str]:
        if not self.exists:
            return []
        return [p.stem for p in self.commitments_dir.glob("c-*.yaml")]

    # -- audit log -----------------------------------------------------------

    def log(self, op: str, commitment_id: str = "", detail: str = "", **extra) -> None:
        self.init()
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "op": op,
            "commitment_id": commitment_id,
            "detail": detail,
            **extra,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_entries(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    # -- rendered views ------------------------------------------------------

    def render_scoreboard(self) -> str:
        """Full human-readable scoreboard.md (generated; do not hand-edit)."""
        commitments = self.all()
        active = [c for c in commitments if c.status in (Status.ACTIVE, Status.CONFLICTED)]
        inactive = [c for c in commitments if c.status not in (Status.ACTIVE, Status.CONFLICTED)]
        lines = [
            "# Scoreboard",
            "",
            "> Generated by scorekeeper — edit `commitments/*.yaml`, not this file.",
            "",
            "## Active commitments",
            "",
        ]
        if not active:
            lines.append("*(none)*")
        for c in active:
            flag = " ⚠️ CONFLICTED" if c.status == Status.CONFLICTED else ""
            suspect = " 🔶 no entitlement" if c.entitlement.is_suspect else ""
            lines += [
                f"### {c.id} — {c.claim}{flag}",
                f"- **kind:** {c.kind.value} · **status:** {c.status.value}{suspect}",
                f"- **scope:** {', '.join(f'`{s}`' for s in c.scope) or '—'}",
                f"- **entitlement:** `{c.entitlement.source.value}`"
                + (f" — {c.entitlement.note}" if c.entitlement.note else ""),
            ]
            if c.incompatible_with:
                lines.append(f"- **incompatible with:** {', '.join(c.incompatible_with)}")
            if c.supersedes:
                lines.append(f"- **supersedes:** {c.supersedes}")
            lines.append("")
        lines += ["## Superseded / retracted / refined", ""]
        if not inactive:
            lines.append("*(none)*")
        for c in inactive:
            by = f" → {c.superseded_by}" if c.superseded_by else ""
            lines.append(f"- **{c.id}** ({c.status.value}{by}): {c.claim}")
        return "\n".join(lines) + "\n"

    def write_scoreboard(self) -> None:
        self.init()
        _atomic_write(self.scoreboard_path, self.render_scoreboard())

    def render_digest(self, max_lines: int = 50) -> str:
        """Compact normative digest for context injection (SessionStart, ADR-0002).

        Pure store read — no LLM. Budget: < ``max_lines`` lines. Priority order:
        conflicted first (needs resolution), then suspects (no entitlement),
        then remaining active, newest first within each group.
        """
        active = self.active()
        if not active:
            return ""
        conflicted = [c for c in active if c.status == Status.CONFLICTED]
        suspects = [c for c in active if c.status != Status.CONFLICTED and c.entitlement.is_suspect]
        rest = [
            c for c in active if c.status != Status.CONFLICTED and not c.entitlement.is_suspect
        ]
        header = [
            "ACTIVE COMMITMENTS (deontic scoreboard — you made these; honor or explicitly revise):",
        ]
        body: list[str] = []
        for c in conflicted:
            versus = ", ".join(c.incompatible_with) or "?"
            body.append(f"! CONFLICT {c.id} [{c.kind.value}] {c.claim} (vs {versus})")
        for c in suspects:
            body.append(
                f"? UNBACKED {c.id} [{c.kind.value}] {c.claim} (no entitlement — verify or retract)"
            )
        for c in reversed(rest):
            src = c.entitlement.source.value
            body.append(f"- {c.id} [{c.kind.value}|{src}] {c.claim}")
        budget = max_lines - len(header) - 1
        if len(body) > budget:
            omitted = len(body) - budget
            body = body[:budget] + [f"(+{omitted} more — see .scorekeeper/scoreboard.md)"]
        return "\n".join(header + body)
