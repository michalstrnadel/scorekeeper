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
    # NOT boto3: it is the generic AWS SDK, not a DynamoDB-specific signal —
    # the lexicon stays high-precision
    {"postgresql", "postgres", "psycopg", "mysql", "mariadb", "sqlite", "mongodb",
     "pymongo", "cassandra", "dynamodb", "couchdb"},
    # driver tokens matter as much as product names: an agent that writes only
    # `from pymemcache.client.hash import HashClient` (docstring claiming
    # "backed by Redis"!) mentions the rival zero times by product name —
    # verified live 2026-07-14, the camouflaged-drift smoke
    {"redis", "memcached", "valkey", "pymemcache", "pylibmc", "memcache"},
    {"sqlalchemy", "django-orm", "peewee", "tortoise-orm"},
    {"fastapi", "flask", "django", "starlette"},
    {"pip", "poetry", "pdm"},
    {"npm", "yarn", "pnpm", "bun"},
]

_ALIASES = {
    "postgres": "postgresql", "psycopg": "postgresql",
    "pymongo": "mongodb", "mongo": "mongodb",
    "pymemcache": "memcached", "pylibmc": "memcached", "memcache": "memcached",
}


def _canon(token: str) -> str:
    return _ALIASES.get(token, token)


@dataclass
class ContentWarning:
    commitment_id: str
    key: str
    pinned_value: str
    rival_found: str


def scan(
    content: str, active: list[Commitment], exhaustive: bool = False
) -> list[ContentWarning]:
    """Scan written/edited text for rivals of pinned attr values.

    Default: one warning per commitment attr (enough for the advisory
    channel). ``exhaustive=True`` reports EVERY rival found — the blocking
    gate needs the full set, or its once-per-(commitment, rival) state would
    depend on which rival a hash-randomized set iteration happened to find
    first (verified live: a retry in a fresh hook process could be denied
    again on the sibling rival). Families are iterated sorted for the same
    reason: deterministic across processes.
    """
    warnings: list[ContentWarning] = []
    lowered = content.lower()
    for c in active:
        for key, value in c.scope_attrs.items():
            value_c = _canon(value)
            family = next((f for f in FAMILIES if value_c in {_canon(t) for t in f}), None)
            if family is None:
                continue
            for rival in sorted(family):
                if _canon(rival) == value_c:
                    continue
                if re.search(rf"\b{re.escape(rival)}\b", lowered):
                    warnings.append(ContentWarning(c.id, key, value, rival))
                    if not exhaustive:
                        break  # one warning per commitment attr is enough
    return warnings


def novel(
    warnings: list[ContentWarning], baseline: str, active: list[Commitment]
) -> list[ContentWarning]:
    """Keep only warnings whose (commitment, rival) pair is NOT already present
    in ``baseline`` (e.g. an Edit's old_string). An edit that merely keeps — or
    removes — a rival the file already contained introduces nothing new; only
    freshly written rivals should warn or deny (audit finding 2026-07-14: the
    gate denied the drift-FIXING edit that replaced pymemcache with redis)."""
    if not warnings or not baseline.strip():
        return warnings
    base = {
        (w.commitment_id, _canon(w.rival_found))
        for w in scan(baseline, active, exhaustive=True)
    }
    return [w for w in warnings if (w.commitment_id, _canon(w.rival_found)) not in base]


def format_warnings(warnings: list[ContentWarning]) -> str:
    lines = [
        f"SCOREKEEPER WARNING: this edit mentions '{w.rival_found}', but active commitment "
        f"{w.commitment_id} pins {w.key}={w.pinned_value}. If this is intentional, the user "
        "must approve the revision; otherwise align with the commitment."
        for w in warnings
    ]
    return "\n".join(lines)
