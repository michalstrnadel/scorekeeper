"""Content-level Tier-0 — instant rival-technology warnings on Edit/Write (ADR-0004).

When the scoreboard pins ``attr:persistence.primary_db=postgresql`` and the
agent writes MongoDB code mid-turn, we do not wait for the Stop-hook LLM pass:
a word-boundary scan against a small rival lexicon flags it in ~ms. This is a
heads-up (additionalContext), never a block — the Stop hook does the real
judgment. The lexicon is deliberately small and high-precision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..model import Commitment

# families of mutually exclusive technology tokens (lowercase)
FAMILIES: list[set[str]] = [
    {"postgresql", "postgres", "mysql", "mariadb", "sqlite", "mongodb", "pymongo",
     "cassandra", "dynamodb", "couchdb"},
    {"redis", "memcached", "valkey"},
    {"sqlalchemy", "django-orm", "peewee", "tortoise-orm"},
    {"fastapi", "flask", "django", "starlette"},
    {"pip", "poetry", "pdm"},
    {"npm", "yarn", "pnpm", "bun"},
]

_ALIASES = {"postgres": "postgresql", "pymongo": "mongodb", "mongo": "mongodb"}


def _canon(token: str) -> str:
    return _ALIASES.get(token, token)


@dataclass
class ContentWarning:
    commitment_id: str
    key: str
    pinned_value: str
    rival_found: str


def scan(content: str, active: list[Commitment]) -> list[ContentWarning]:
    """Scan written/edited text for rivals of pinned attr values."""
    warnings: list[ContentWarning] = []
    lowered = content.lower()
    for c in active:
        for key, value in c.scope_attrs.items():
            value_c = _canon(value)
            family = next((f for f in FAMILIES if value_c in {_canon(t) for t in f}), None)
            if family is None:
                continue
            for rival in family:
                if _canon(rival) == value_c:
                    continue
                if re.search(rf"\b{re.escape(rival)}\b", lowered):
                    warnings.append(ContentWarning(c.id, key, value, rival))
                    break  # one warning per commitment attr is enough
    return warnings


def format_warnings(warnings: list[ContentWarning]) -> str:
    lines = [
        f"SCOREKEEPER WARNING: this edit mentions '{w.rival_found}', but active commitment "
        f"{w.commitment_id} pins {w.key}={w.pinned_value}. If this is intentional, the user "
        "must approve the revision; otherwise align with the commitment."
        for w in warnings
    ]
    return "\n".join(lines)
