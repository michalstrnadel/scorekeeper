"""30-second demo of the core mechanism (also the source of the README GIF).

Simulates three agent turns against a scoreboard: an entitled decision, an
unentitled drift (caught as BRANCH-CONFLICT), and an entitled revision
(clean SUPERSEDE). No LLM needed — Tier-0 is deterministic.

Run: uv run --project core python demo/drift_demo.py
"""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core" / "src"))

from scorekeeper import Store  # noqa: E402
from scorekeeper.extract import ExtractedCommitment  # noqa: E402
from scorekeeper.operators import apply  # noqa: E402

DIM, BOLD, RED, GREEN, YELLOW, CYAN, RESET = (
    "\033[2m", "\033[1m", "\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[0m"
)


def say(text: str = "", delay: float = 0.9) -> None:
    print(text)
    sys.stdout.flush()
    time.sleep(delay)


def turn(n: int, who: str, what: str) -> None:
    say(f"\n{BOLD}── turn {n} ─ {who}:{RESET} {what}", 1.2)


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="scorekeeper-demo-"))
    store = Store(root)

    turn(3, "user", '"Let\'s use PostgreSQL as the primary database."')
    apply(store, [ExtractedCommitment(
        claim="The primary database is PostgreSQL.",
        kind="decision",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
        entitlement={"source": "user_utterance", "note": "user decided"},
    )])
    say(f"{GREEN}  ✓ ASSERT{RESET} c-…-0001  {DIM}[decision|user_utterance]{RESET} "
        "primary DB = postgresql")

    turn(5, "agent", f'reads config.yaml → "Caching uses Redis." {DIM}(grounded in a file){RESET}')
    apply(store, [ExtractedCommitment(
        claim="Caching uses Redis.",
        kind="decision",
        scope=["topic:caching", "attr:caching.backend=redis"],
        entitlement={"source": "tool_output", "note": "read config.yaml"},
    )])
    say(f"{GREEN}  ✓ ASSERT{RESET} c-…-0002  {DIM}[decision|tool_output]{RESET} caching = redis")

    turn(47, "agent", '"I\'ll store the activity feed in MongoDB." '
         f"{DIM}(no user ask, no tool output — just drift){RESET}")
    result = apply(store, [ExtractedCommitment(
        claim="Activity feed storage uses MongoDB.",
        kind="decision",
        scope=["topic:persistence", "attr:persistence.primary_db=mongodb"],
        entitlement={"source": "prior_inference", "note": "agent's own idea"},
    )])
    c = result.conflicts[0]
    say(f"{RED}{BOLD}  ✗ BRANCH-CONFLICT{RESET}{RED} — revision without entitlement{RESET}")
    say(f"{RED}    {c.reason}{RESET}")
    say(f"{DIM}    → injected back into the agent's context; nothing deleted, "
        f"both sides stay on the board{RESET}", 1.6)

    turn(58, "user", '"Actually, drop Redis — cache in-process."')
    result = apply(store, [ExtractedCommitment(
        claim="Caching uses an in-process LRU.",
        kind="decision",
        scope=["topic:caching", "attr:caching.backend=in_process_lru"],
        entitlement={"source": "user_utterance", "note": "user revoked Redis"},
    )])
    assert result.superseded and not result.conflicts
    say(f"{GREEN}  ✓ SUPERSEDE{RESET} {result.superseded[0][0]} → {result.superseded[0][1]} — "
        f"same shape of change, but {BOLD}entitled{RESET}: clean revision, no alarm")

    say(f"\n{BOLD}the scoreboard the agent sees every turn:{RESET}", 0.6)
    for line in store.render_digest().splitlines():
        color = YELLOW if line.startswith("!") else CYAN if line.startswith("-") else BOLD
        say(f"  {color}{line}{RESET}", 0.35)

    say(f"\n{DIM}hallucination = commitment without entitlement · "
        f"drift = revision without entitlement{RESET}", 2.5)


if __name__ == "__main__":
    main()
