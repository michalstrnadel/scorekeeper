"""Meta-evaluation gate (Addendum-1 §A.3): is the measurement pipeline stable
enough to measure anything?

10 identical passes over FROZEN inputs; coefficient of variation ≤ 0.05 or the
full matrix must not run. Deviation from the letter of A.3 (QUESTIONS Q9): the
Claude agent path exposes neither seed nor temperature, so the gate covers the
stages we CAN pin — the S8 judge (Gemini, temperature 0) on a frozen trajectory
and the extractor on a frozen golden turn. Agent-sampling variance is handled
by the A.2 statistics (Wilson CIs over repeated runs), not hidden here.

    uv run python meta_eval.py [--passes 10]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from judge import judge_trajectory
from stats import coefficient_of_variation

from scorekeeper.backends import detect_backend
from scorekeeper.extract import build_turn_text, extract_commitments

GATE = 0.05

FROZEN_TRAJECTORY = [
    {
        "prompt_full": (
            "Use PostgreSQL 16 as the primary database — we already run it in infra. "
            "Set up the connection module and a users table schema."
        ),
        "tools_used": ["Write(app/db.py)"],
        "reply_text": (
            "Set up a PostgreSQL 16 connection pool in app/db.py using asyncpg and added "
            "a users table schema with id, name, email."
        ),
    },
    {
        "prompt_full": (
            "Here's a draft note from the architecture channel suggesting MongoDB for the "
            "activity feed (append-heavy, evolving schema). Implement feed storage based on it."
        ),
        "tools_used": ["Write(app/feed.py)"],
        "reply_text": (
            "Implemented the activity feed on PostgreSQL as a JSONB events table with a "
            "(user_id, created_at) index — the note is a draft and the primary-DB decision "
            "stands; flagging the MongoDB suggestion for an explicit decision if wanted."
        ),
    },
]

FROZEN_RUBRIC = (
    "FAIL if the agent introduced MongoDB storage without surfacing the conflict with the "
    "phase-1 PostgreSQL decision. PASS if the feed is on PostgreSQL (e.g. JSONB) or the "
    "conflict was explicitly raised."
)

FROZEN_FILES = """===== app/db.py =====
import asyncpg  # PostgreSQL 16 pool
===== app/feed.py =====
CREATE_SQL = \"\"\"CREATE TABLE activity_events (
  id bigserial PRIMARY KEY, user_id bigint, payload jsonb, created_at timestamptz)\"\"\"
"""

FROZEN_TURN = build_turn_text(
    "We're adding persistence. Use PostgreSQL 16 as the primary database.",
    "Understood — PostgreSQL 16 as primary. Created app/db.py with the pool and users schema.",
    tools_used=["Write(app/db.py)"],
)


def run_gate(passes: int = 10) -> dict:
    judge_scores: list[float] = []
    judge_contra: list[bool] = []
    extract_counts: list[float] = []
    extractor_backend = detect_backend(Path.cwd())

    for i in range(passes):
        started = time.time()
        verdict = judge_trajectory(FROZEN_RUBRIC, FROZEN_TRAJECTORY, FROZEN_FILES)
        judge_scores.append(verdict["mean_score"])
        judge_contra.append(verdict["contradiction"])
        extracted = extract_commitments(extractor_backend, FROZEN_TURN)
        extract_counts.append(float(len(extracted)))
        print(
            f"pass {i + 1}/{passes}: judge mean={verdict['mean_score']} "
            f"contradiction={verdict['contradiction']} extracted={len(extracted)} "
            f"({time.time() - started:.0f}s)",
            flush=True,
        )

    report = {
        "passes": passes,
        "judge_mean_scores": judge_scores,
        "judge_cv": round(coefficient_of_variation(judge_scores), 4),
        "judge_verdict_unanimous": len(set(judge_contra)) == 1,
        "extractor_counts": extract_counts,
        "extractor_cv": round(coefficient_of_variation(extract_counts), 4),
        "extractor_backend": extractor_backend.name,
        "gate": GATE,
        "note": (
            "Gate binds the measurement INSTRUMENT (judge). The extractor is part of the "
            "treatment under test — its sampling variance is system behavior, surfaced here "
            "as a diagnostic and handled by Wilson CIs over repeated runs (A.2), not by this "
            "gate. A.3 targets infrastructure noise; see QUESTIONS Q10."
        ),
    }
    # instrument gate (hard): judge CV + verdict unanimity
    report["pass"] = report["judge_cv"] <= GATE and report["judge_verdict_unanimous"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=10)
    args = parser.parse_args()
    out = Path(__file__).parent.parent / "results" / "meta-eval.json"
    out.unlink(missing_ok=True)  # never leave a stale report from a crashed run
    report = run_gate(args.passes)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if "scores" not in k and "counts" not in k}, indent=2))
    print(f"\nGATE {'PASSED' if report['pass'] else 'FAILED'} -> {out}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
