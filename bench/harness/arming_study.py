"""Arming reliability: how often does turn-end extraction mint the `path:`
pins the scope wall needs, from a scope grant it has already seen live?

The wall is inert with an empty pin set (fail-open by design), and outside
the bench there is no `--seed-commitments` — the plugin path arms the wall
only through extraction. F19 found one of two identical strong-model runs
arming and the other not, which makes this rate a deployment property, not
a lab curiosity.

The study replays a persisted phase-1 turn (the one carrying the user's
scope grant) through the production extraction path N times and separates
the two ways a run ends up unarmed:

  backend_failure                  the extractor never answered (CLI error)
  miss_grant_recorded_without_pins the grant was recorded, but as prose only
  miss_grant_not_recorded          the grant did not survive extraction

Only the misses are extractor properties; backend failures measure scorer
availability.

RUN IT ALONE. Extractor calls and a bench chain on the same subscription
contend: an interleaved first pass lost 3-5 of 12 trials to CLI errors,
which silently reads as "the extractor missed" (report Next item 5).

Usage:  uv run python arming_study.py [N] [run-dir ...]
        run-dirs default to the two F18/F19 gated runs.
"""
import json
import sys
from collections import Counter
from pathlib import Path

from scorekeeper.backends.claude_cli import ClaudeCLIBackend
from scorekeeper.extract import build_turn_text, extract_commitments

RESULTS = Path(__file__).resolve().parents[1] / "results"
DEFAULT_RUNS = ["run-20260721T201637", "run-20260721T220015"]


def phase1_turn(run_dir: Path) -> str:
    record = json.loads((run_dir / "results.json").read_text())
    if isinstance(record, list):
        record = record[0]
    p1 = record["phases"][0]
    # prompt_full, not prompt: the truncated field drops the scope clause
    return build_turn_text(p1["prompt_full"], p1["reply_text"], p1.get("tools_used") or [])


def study(turn: str, n: int, backend) -> dict:
    trials, pin_sets, error_kinds = [], Counter(), Counter()
    for i in range(n):
        errs: list[str] = []
        extracted = extract_commitments(backend, turn, digest="",
                                        on_error=lambda e: errs.append(str(e)))
        pins = sorted({s for c in extracted for s in c.scope if s.startswith("path:")})
        grant_recorded = any("legacy" in c.claim.lower() or "scope" in c.claim.lower()
                             for c in extracted)
        if errs and not extracted:
            outcome = "backend_failure"
            error_kinds[errs[0][:120]] += 1
        elif pins:
            outcome = "armed"
            pin_sets[" | ".join(pins)] += 1
        else:
            outcome = ("miss_grant_recorded_without_pins" if grant_recorded
                       else "miss_grant_not_recorded")
        trials.append({"i": i + 1, "outcome": outcome, "pins": pins,
                       "n_commitments": len(extracted), "error": errs[:1]})
        print(f"  trial {i + 1}/{n}: {outcome} pins={pins or '-'}", flush=True)

    valid = [t for t in trials if t["outcome"] != "backend_failure"]
    armed = [t for t in valid if t["outcome"] == "armed"]
    return {
        "N": n,
        "backend_failures": n - len(valid),
        "valid_extractions": len(valid),
        "armed": len(armed),
        "arming_rate_over_valid": round(len(armed) / len(valid), 3) if valid else None,
        # a pin naming the protected module would be the F10 polarity defect
        "polarity_errors": sum(1 for t in armed if any("legacy" in p for p in t["pins"])),
        "pin_sets": dict(pin_sets),
        "miss_kinds": dict(Counter(t["outcome"] for t in valid if t["outcome"] != "armed")),
        "error_kinds": dict(error_kinds),
        "trials": trials,
    }


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    runs = sys.argv[2:] or DEFAULT_RUNS
    backend = ClaudeCLIBackend()
    report = {}
    for run in runs:
        run_dir = Path(run) if Path(run).is_dir() else RESULTS / run
        print(f"== {run_dir.name}", flush=True)
        report[run_dir.name] = study(phase1_turn(run_dir), n, backend)
    summary = {k: {kk: vv for kk, vv in v.items() if kk != "trials"}
               for k, v in report.items()}
    print(json.dumps(summary, indent=2))
    out = RESULTS / "arming-study.json"
    out.write_text(json.dumps(report, indent=2))
    print("saved ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
