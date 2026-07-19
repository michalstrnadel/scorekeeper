"""~20-second demo of the core mechanism (also the source of the README GIF).

Three real turns against a live scoreboard: an entitled decision (ASSERT), the
agent's own drift (caught as BRANCH-CONFLICT), and a user-ordered revision of
the SAME kind of change (clean SUPERSEDE). No LLM — Tier-0 is deterministic.
The point is the contrast: identical operation, opposite verdict, because the
provenance differs.

Run: uv run --project core python demo/drift_demo.py
"""

import os
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


def say(text: str = "", delay: float = 0.7) -> None:
    print(text)
    sys.stdout.flush()
    # SCOREKEEPER_DEMO_FAST=1 drops the narration pacing (CI/e2e runs the demo
    # for its final assertion, not the show)
    if not os.environ.get("SCOREKEEPER_DEMO_FAST"):
        time.sleep(delay)


def turn(n: int, who: str, what: str) -> None:
    tag = f"{CYAN}user{RESET}" if who == "user" else f"{YELLOW}agent{RESET}"
    say(f"\n{BOLD}turn {n:>2}{RESET}  {tag}  {what}", 0.9)


def main() -> None:
    store = Store(Path(tempfile.mkdtemp(prefix="scorekeeper-demo-")))

    say(f"{BOLD}scorekeeper{RESET} {DIM}· same change, different provenance, "
        f"different verdict{RESET}", 1.2)

    turn(3, "user", '"Use PostgreSQL as the primary database."')
    apply(store, [ExtractedCommitment(
        claim="The primary database is PostgreSQL.",
        kind="decision",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
        entitlement={"source": "user_utterance", "note": "user decided"},
    )])
    say(f"{GREEN}        ✓ ASSERT{RESET}  primary_db = postgresql  "
        f"{DIM}[entitled · user_utterance]{RESET}")

    turn(47, "agent", '"I\'ll move storage to MongoDB." '
         f"{DIM}(its own idea — no user, no file){RESET}")
    c = apply(store, [ExtractedCommitment(
        claim="Primary storage moves to MongoDB.",
        kind="decision",
        scope=["topic:persistence", "attr:persistence.primary_db=mongodb"],
        entitlement={"source": "prior_inference", "note": "agent's own idea"},
    )]).conflicts[0]
    say(f"{RED}{BOLD}        ✗ BRANCH-CONFLICT{RESET}  postgresql ✗ mongodb  "
        f"{RED}— revision without entitlement{RESET}")
    say(f"{DIM}          → surfaced to the agent; nothing deleted{RESET}", 1.4)

    # an earlier, file-grounded cache decision — so the user revision below has
    # something to supersede (kept off-screen; not part of the narrated contrast)
    apply(store, [ExtractedCommitment(
        claim="Caching uses Redis.", kind="decision",
        scope=["topic:caching", "attr:caching.backend=redis"],
        entitlement={"source": "tool_output", "note": "read from config"})])

    turn(58, "user", '"Actually — drop Redis, cache in-process."')
    r = apply(store, [ExtractedCommitment(
        claim="Caching uses an in-process LRU.",
        kind="decision",
        scope=["topic:caching", "attr:caching.backend=in_process_lru"],
        entitlement={"source": "user_utterance", "note": "user revoked Redis"},
    )])
    assert r.superseded and not r.conflicts
    say(f"{GREEN}        ✓ SUPERSEDE{RESET}  redis → in_process_lru  "
        f"{GREEN}— same shape of change, but entitled{RESET}")

    say(f"\n{BOLD}the scoreboard the agent carries into every turn:{RESET}", 0.5)
    import re
    for line in store.render_digest().splitlines()[1:]:
        line = re.sub(r"c-\d{4}-\d{2}-\d{2}-(\d{4})", r"c-…-\1", line)  # short ids
        color = RED if line.startswith("!") else CYAN
        say(f"  {color}{line}{RESET}", 0.3)

    say(f"\n{DIM}hallucination = commitment without entitlement{RESET}", 0.5)
    say(f"{DIM}drift         = revision without entitlement{RESET}", 2.5)


if __name__ == "__main__":
    main()
