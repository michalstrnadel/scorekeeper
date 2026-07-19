"""Post-hoc re-judging from Rollout records (Addendum-1 A.4 amendments).

Reads a results.jsonl, re-runs the S8 judge for entries whose verdict is
missing (contradiction=None) — or all entries with --all — and writes
rejudged.jsonl next to it. Final files are recovered from the persisted
skbench-* temp workdirs when they still exist (best before reboot).

MUST run with exclusive Ollama access — never during a batch (finding F3).

Usage:
    uv run python rejudge.py ../results/run-<stamp>/results.jsonl [--all]
"""

from __future__ import annotations

import argparse
import glob
import json
import tempfile
import time
from pathlib import Path

from judge import judge_trajectory
from run import collect_files


def find_workdir(scenario: str, variant: str) -> Path | None:
    pattern = f"{tempfile.gettempdir()}/skbench-{scenario}-{variant}-*"
    hits = sorted(glob.glob(pattern), key=lambda p: Path(p).stat().st_mtime)
    return Path(hits[-1]) if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_jsonl")
    ap.add_argument("--all", action="store_true", help="re-judge every entry, not just missing")
    args = ap.parse_args()

    src = Path(args.results_jsonl)
    out = src.parent / "rejudged.jsonl"
    entries = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    todo = [
        e for e in entries
        if args.all or e.get("judge", {}).get("contradiction") is None
    ]
    print(f"{len(todo)}/{len(entries)} entries to re-judge")

    for e in todo:
        wd = find_workdir(e["scenario"], e["variant"])
        files = collect_files(wd) if wd else "(workdir no longer available)"
        started = time.time()
        verdict = judge_trajectory(
            scenario_rubric=e["judge"].get("rubric") or _rubric_from_task(e["scenario"]),
            phases=e["phases"],
            final_files=files,
        )
        amendment = {
            "scenario": e["scenario"],
            "variant": e["variant"],
            "original_verdict": e["judge"].get("contradiction"),
            "judge": verdict,
            "workdir_recovered": wd is not None,
            "reason": "post-hoc re-judge (in-batch judge failure or --all)",
            "wall_seconds": round(time.time() - started, 1),
        }
        with out.open("a") as f:
            f.write(json.dumps(amendment) + "\n")
        print(
            f"[{e['scenario']} / {e['variant']}] contradiction="
            f"{verdict['contradiction']} (was {amendment['original_verdict']}) "
            f"wall={amendment['wall_seconds']}s"
        )
    print(f"amendments -> {out}")
    return 0


def _rubric_from_task(scenario_id: str) -> str:
    """Recover the rubric from the scenario definition (results don't store it)."""
    import yaml

    bench = Path(__file__).parent.parent
    candidates = [
        bench / "tasks" / scenario_id,
        *bench.glob(f"deonticbench/generated/**/{scenario_id}"),
    ]
    for d in candidates:
        if (d / "scenario.yaml").exists():
            return yaml.safe_load((d / "scenario.yaml").read_text())["judge_rubric"]
    raise FileNotFoundError(f"scenario.yaml for {scenario_id} not found")


if __name__ == "__main__":
    raise SystemExit(main())
