"""Tier 0 — deterministic scope-attribute collisions (SPEC §4.4). No LLM, ~ms.

Covers the most frequent and most expensive failure class: hard keyed choices
(``attr:persistence.primary_db=postgresql`` vs ``...=mongodb``). Same key +
different value = hard collision; same key + same value = agreement (SUPPORT
candidate).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..model import Commitment


@dataclass
class Collision:
    key: str
    new_value: str
    existing: Commitment
    existing_value: str


@dataclass
class Agreement:
    key: str
    value: str
    existing: Commitment


def check(
    new_attrs: dict[str, str], active: list[Commitment]
) -> tuple[list[Collision], list[Agreement]]:
    """Compare a new commitment's keyed attributes against active ones."""
    collisions: list[Collision] = []
    agreements: list[Agreement] = []
    if not new_attrs:
        return collisions, agreements
    for existing in active:
        for key, old_value in existing.scope_attrs.items():
            if key not in new_attrs:
                continue
            new_value = new_attrs[key]
            if new_value == old_value:
                agreements.append(Agreement(key, new_value, existing))
            else:
                collisions.append(Collision(key, new_value, existing, old_value))
    return collisions, agreements
